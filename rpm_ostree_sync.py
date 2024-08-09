import subprocess
import json
import os

def get_installed_packages():
    """Get the list of installed packages using rpm-ostree."""
    result = subprocess.run(['rpm-ostree', 'status', '--json'], capture_output=True, text=True)
    status = json.loads(result.stdout)
    return status[0]['packages']

def sync_packages(remote_host):
    """Synchronize packages with a remote host using Unison."""
    local_packages = get_installed_packages()
    
    # Write local packages to a file
    with open('local_packages.txt', 'w') as f:
        for package in local_packages:
            f.write(f"{package}\n")
    
    # Use Unison to synchronize the package list
    subprocess.run(['unison', 'local_packages.txt', f'ssh://{remote_host}/remote_packages.txt'])
    
    # Read the synchronized package list
    with open('local_packages.txt', 'r') as f:
        synced_packages = set(f.read().splitlines())
    
    # Compare and install missing packages
    current_packages = set(get_installed_packages())
    packages_to_install = synced_packages - current_packages
    
    if packages_to_install:
        print(f"Installing missing packages: {', '.join(packages_to_install)}")
        subprocess.run(['rpm-ostree', 'install'] + list(packages_to_install))
    else:
        print("No new packages to install.")

if __name__ == "__main__":
    remote_host = input("Enter the remote host to synchronize with: ")
    sync_packages(remote_host)
