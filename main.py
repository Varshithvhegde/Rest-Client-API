import paramiko
import tkinter as tk
from tkinter import ttk
import json
from colorama import init, Fore
from ttkthemes import ThemedTk
from Placeholder import PlaceholderEntry
import socket
import threading
import time

# Initialize colorama for colored output
init()

class CustomRestClient:
    def __init__(self, ssh_host, ssh_username, ssh_password):
        self.ssh_host = ssh_host
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.ssh_client = paramiko.SSHClient()
        self.connected = False
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.check_connection_thread = threading.Thread(target=self.check_connection)
        self.check_connection_thread.daemon = True
        self.check_connection_thread.start()

    def connect_ssh(self):
        try:
            self.ssh_client.connect(hostname=self.ssh_host, username=self.ssh_username, password=self.ssh_password, timeout=10)
            print(Fore.GREEN + "SSH connection established successfully.")
            self.connected = True
            connection_status_label.config(text="Connected", foreground="green")
            connect_button.config(state="disabled")  # Disable the button after successful connection
        except paramiko.AuthenticationException as auth_err:
            print(Fore.RED + f"Authentication error occurred: {auth_err}")
            self.connected = False
            connection_status_label.config(text="Disconnected", foreground="red")
            connect_button.config(state="normal")  # Enable the button after failed connection
        except paramiko.SSHException as ssh_err:
            print(Fore.RED + f"SSH error occurred: {ssh_err}")
            self.connected = False
            connection_status_label.config(text="Disconnected", foreground="red")
            connect_button.config(state="normal")  # Enable the button after failed connection
        except Exception as err:
            print(Fore.RED + f"An error occurred: {err}")
            self.connected = False
            connection_status_label.config(text="Disconnected", foreground="red")
            connect_button.config(state="normal")  # Enable the button after failed connection

    def execute_command(self, command):
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8")
            if error:
                print(Fore.RED + f"Error occurred: {error}")
            return output
        except Exception as err:
            print(Fore.RED + f"An error occurred: {err}")

    def check_connection(self):
        while True:
            if self.connected:
                try:
                    self.ssh_client.exec_command("echo", timeout=5)
                except (paramiko.SSHException, socket.error):
                    print(Fore.RED + "SSH connection closed by remote host.")
                    self.connected = False
                    connection_status_label.config(text="Disconnected", foreground="red")
                    connect_button.config(state="normal")  # Enable the button after disconnection
            time.sleep(10)  # Check connection every 10 seconds

# def get_data():
#     if not client.connected:
#         print(Fore.RED + "Not connected to SSH. Please connect first.")
#         return

#     url = entry.get()
#     method = method_var.get()
#     curl_command = f"curl -X {method} {url}"
    
#     # Include data for POST and PUT requests
#     if method in ['POST', 'PUT']:
#         data = data_entry.get("1.0", tk.END).strip()
#         curl_command += f" -d '{data}'"
    
#     response = client.execute_command(curl_command)
#     if response:
#         try:
#             json_data = json.loads(response)
#             formatted_json = json.dumps(json_data, indent=4)
#             output_text.config(state="normal")
#             output_text.delete("1.0", tk.END)
#             output_text.insert(tk.END, formatted_json)
#             output_text.config(state="disabled")
#         except Exception as e:
#             print(Fore.RED + "Error parsing JSON:", e)
def get_data():
    if not client.connected:
        print(Fore.RED + "Not connected to SSH. Please connect first.")
        return

    url = entry.get()
    if not url:
        output_text.config(state="normal")
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, "Error: URL cannot be empty\n")
        output_text.config(state="disabled")
        return

    method = method_var.get()
    if method not in ['GET', 'POST', 'PUT', 'DELETE']:
        output_text.config(state="normal")
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, "Error: Invalid HTTP request method\n")
        output_text.config(state="disabled")
        return

    curl_command = f"curl -X {method} {url}"
    
    # Include data for POST and PUT requests
    if method in ['POST', 'PUT']:
        data = data_entry.get("1.0", tk.END).strip()
        curl_command += f" -d '{data}'"
    
    response = client.execute_command(curl_command)
    if response:
        try:
            json_data = json.loads(response)
            formatted_json = json.dumps(json_data, indent=4)
            output_text.config(state="normal")
            output_text.delete("1.0", tk.END)
            output_text.insert(tk.END, formatted_json)
            output_text.config(state="disabled")
        except Exception as e:
            print(Fore.RED + "Error parsing JSON:", e)
            output_text.config(state="normal")
            output_text.delete("1.0", tk.END)
            output_text.insert(tk.END, f"Error parsing JSON: {e}\n")
            output_text.config(state="disabled")


def connect_ssh():
    try:
        client.connect_ssh()
    except socket.error as sock_err:
        print(Fore.RED + f"Socket error occurred: {sock_err}")
        connection_status_label.config(text="Disconnected", foreground="red")
        connect_button.config(state="normal")  # Enable the button after socket error

def search_text():
    search_str = search_entry.get()
    if search_str:
        start = "1.0"
        output_text.tag_remove("found", "1.0", tk.END)  # Clear previous search highlights
        while True:
            start = output_text.search(search_str, start, stopindex=tk.END)
            if not start:
                break
            end = f"{start}+{len(search_str)}c"
            output_text.tag_add("found", start, end)
            start = end
        output_text.tag_config("found", background="yellow")
        output_text.focus_set()

def next_result():
    search_str = search_entry.get()
    start = output_text.index("insert")
    start = output_text.search(search_str, f"{start}+1c", stopindex=tk.END)
    if start:
        end = f"{start}+{len(search_str)}c"
        output_text.tag_add("found", start, end)
        output_text.tag_config("found", background="yellow")
        output_text.see(start)
    else:
        print("No more results")

if __name__ == "__main__":
    ssh_host = "192.168.1.4"
    ssh_username = "root"
    ssh_password = "root"

    client = CustomRestClient(ssh_host, ssh_username, ssh_password)

    root = ThemedTk(theme="breeze")
    root.title("Custom REST Client")
    
    connect_button = ttk.Button(root, text="Connect SSH", command=connect_ssh)
    connect_button.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
    
    label_method = ttk.Label(root, text="Method:")
    label_method.grid(row=1, column=0, padx=5, pady=5)

    method_var = tk.StringVar()
    method_var.set("GET")
    method_dropdown = ttk.OptionMenu(root, method_var, "GET", "GET", "POST", "PUT", "DELETE")
    method_dropdown.grid(row=2, column=0 ,padx=5, pady=5)

    entry = PlaceholderEntry(root, width=50, placeholder="Enter URL endpoint(127.0.0.1<port>/<endpoint)")
    entry.grid(row=2, column=1, padx=5, pady=5)

    get_data_button = ttk.Button(root, text="Send Request", command=get_data)
    get_data_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

    search_frame = ttk.Frame(root)
    search_frame.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
    search_label = ttk.Label(search_frame, text="Search:")
    search_label.pack(side="left")
    search_entry = ttk.Entry(search_frame, width=30)
    search_entry.pack(side="left")
    search_button = ttk.Button(search_frame, text="Search", command=search_text)
    search_button.pack(side="left")

    data_label = ttk.Label(root, text="Data (for POST and PUT):")
    data_label.grid(row=3, column=0, padx=5, pady=5)

    data_entry = tk.Text(root, wrap="word", height=5, width=50)
    data_entry.grid(row=3, column=1, padx=5, pady=5)

    output_text = tk.Text(root, wrap="word", height=20, width=70, state="disabled")
    output_text.grid(row=7, column=0, columnspan=2, padx=5, pady=5)

    connection_status_label = ttk.Label(root, text="Disconnected", foreground="red")
    connection_status_label.grid(row=8, column=0, columnspan=2, padx=5, pady=5)

    root.mainloop()
