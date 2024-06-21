import os
import requests
from datetime import datetime
from tqdm import tqdm
import logging
import urllib3
import threading
from concurrent.futures import ThreadPoolExecutor
from dateutil.relativedelta import relativedelta

# Configure general execution logging
logging.basicConfig(filename='execution_log.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Function to configure logging for each test case
def configure_testcase_logging(test_case_id):
    logger = logging.getLogger(test_case_id)
    logger.setLevel(logging.DEBUG)
    # Log file handler for both normal and error logs
    file_handler = logging.FileHandler(f"{test_case_id}_log.log")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

# Function to get the Bearer token
def get_bearer_token():
    default_token = "**************************"
    user_token = input("Enter your Bearer token (press Enter to use default token): ").strip()
    return user_token if user_token else default_token

# Define the API endpoints and headers
test_run_url_template = "https://jira.jnd.joynext.com/rest/raven/1.0/test/{}/testrun"
step_url_template = "https://jira.jnd.joynext.com/rest/raven/1.0/testrun/{}/steps"
download_url_template = "https://jira.jnd.joynext.com/plugins/servlet/raven/attachment/{}/{}"


def parse_relative_date(date_str):
    if "days ago" in date_str:
        days_ago = int(date_str.split()[0])
        return datetime.now() - relativedelta(days=days_ago)
    else:
        return datetime.strptime(date_str, "%d.%m.%Y %I:%M %p")
    
# Function to get test runs for a test case
# Function to get test runs for a test case
def get_test_runs(test_case_id, testcase_logger, headers):
    test_run_url = test_run_url_template.format(test_case_id)
    testcase_logger.info(f"{datetime.now()} - Fetching test runs for test case {test_case_id}")
    response = requests.get(test_run_url, headers=headers, verify=False)
    testcase_logger.debug(f"{datetime.now()} - Test run URL: {test_run_url}")
    testcase_logger.debug(f"{datetime.now()} - Response: {response}")
    if response.status_code == 200:
        test_run_data = response.json()
        test_runs = []
        for entry in test_run_data["entries"]:
            testrun_started = entry["userColumns"]["testrun_started"]
            if testrun_started:  # Check if testrun_started is not empty
                # Parse the date string
                testrun_started_date = parse_relative_date(testrun_started)
                # Compare with the specified date
                if testrun_started_date > datetime(2023, 10, 1):
                    test_run_id = entry["testRunId"]
                    test_run_key = entry["key"]
                    # Append the function call to the list
                    test_runs.append((test_case_id, test_run_id, test_run_key, headers, testcase_logger))
        return test_runs
    else:
        testcase_logger.error(f"{datetime.now()} - Failed to fetch test runs for test case {test_case_id}")
        return []

# Function to get evidences for a test run
def get_evidences(test_run_id, testcase_logger, headers):
    step_url = step_url_template.format(test_run_id)
    testcase_logger.info(f"{datetime.now()} - Fetching evidences for test run ID: {test_run_id}")
    response = requests.post(step_url, headers=headers, verify=False)
    testcase_logger.debug(f"{datetime.now()} - Step URL: {step_url}")
    testcase_logger.debug(f"{datetime.now()} - Response: {response}")
    if response.status_code == 200:
        steps_data = response.json()["stepResults"]
        evidences = []
        for step in steps_data:
            if "evidences" in step:
                evidences.extend(step["evidences"])
        
        # Check the new URL for additional evidence
        attachment_url = f"https://jira.jnd.joynext.com/rest/raven/1.0/testrun/{test_run_id}/attachment"
        testcase_logger.info(f"{datetime.now()} - Fetching additional evidences from: {attachment_url}")
        attachment_response = requests.get(attachment_url, headers=headers, verify=False)
        testcase_logger.debug(f"{datetime.now()} - Attachment URL: {attachment_url}")
        testcase_logger.debug(f"{datetime.now()} - Response: {attachment_response}")
        if attachment_response.status_code == 200:
            additional_evidences = attachment_response.json()
            if additional_evidences:
                evidences.extend(additional_evidences)
        
        return evidences
    else:
        testcase_logger.error(f"{datetime.now()} - Failed to fetch evidences for test run ID: {test_run_id}")
        return []

# Function to download evidence
def download_evidence(evidence, test_case, test_run_id, test_run_key, headers, testcase_logger):
    download_url = download_url_template.format(evidence["id"], evidence["fileName"])
    testcase_logger.info(f"{datetime.now()} - Downloading evidence: {evidence['fileName']} for test run ID: {test_run_id}")
    response = requests.get(download_url, headers=headers, verify=False, stream=True)  # Stream the response
    testcase_logger.debug(f"{datetime.now()} - Download URL: {download_url}")
    testcase_logger.debug(f"{datetime.now()} - Response: {response}")
    if response.status_code == 200:
        folder_path = os.path.join("test_case", test_case.strip(), test_run_key)
        os.makedirs(folder_path, exist_ok=True)
        
        # Append a unique identifier to the file name if it already exists
        file_name = evidence["fileName"]
        file_path = os.path.join(folder_path, file_name)
        count = 1
        while os.path.exists(file_path):
            file_name, ext = os.path.splitext(evidence["fileName"])
            file_name = f"{file_name}_{count}{ext}"
            file_path = os.path.join(folder_path, file_name)
            count += 1
        
        # Get the total file size for the progress bar
        total_size = int(response.headers.get('content-length', 0))
        
        # Create the progress bar
        progress_bar = tqdm(total=total_size, unit='B', unit_scale=True, desc=f'Downloading {file_name}')
        
        # Download the file and update the progress bar
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
                    progress_bar.update(len(chunk))
        
        # Close the progress bar
        progress_bar.close()
        
        # Log the download event into the log file with date and time
        log_message = f"{datetime.now()} - Downloaded evidence: {file_name} for test Execution : {test_run_key}"
        testcase_logger.info(log_message)
        print(log_message)
    else:
        # Log the error event into the log file with date and time
        error_message = f"{datetime.now()} - Failed to download evidence for test run ID : {test_run_id} and key: {test_run_key}"
        testcase_logger.error(error_message)
        print(error_message)

# Function to download evidence for a single test run
def download_test_run_evidence(test_case_id, test_run_id, test_run_key, headers, testcase_logger):
    testcase_logger = configure_testcase_logging(test_case_id)
    testcase_logger.info(f"{datetime.now()} - Processing test case: {test_case_id}")
    print(f"Processing test case: {test_case_id}")
    # Get evidences for the test run
    evidences = get_evidences(test_run_id, testcase_logger, headers)
    for evidence in evidences:
        download_evidence(evidence, test_case_id.strip(), test_run_id, test_run_key, headers, testcase_logger)
    print(f"Download completed for Test Case: {test_case_id}, Test Run: {test_run_key}")
    testcase_logger.info(f"Download completed for Test Case: {test_case_id}, Test Run: {test_run_key}")
    logging.info(f"Download completed for Test Case: {test_case_id}, Test Run: {test_run_key}")

# Main function
def main():
    # Get Bearer token
    token = get_bearer_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    test_cases = input("Enter test cases (comma-separated): ").strip().split(",")
    # Limit the number of threads to 3
    max_threads = 3
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        for test_case_id in test_cases:
            test_runs = get_test_runs(test_case_id.strip(), logging.getLogger(), headers)
            for test_run in test_runs:
                executor.submit(download_test_run_evidence, *test_run)

    print(f"------Downloading Evidence Completed for all TCs------")

if __name__ == "__main__":
    main()
