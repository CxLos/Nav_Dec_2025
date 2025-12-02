import os
import requests
import base64
from dotenv import load_dotenv
from typing import List, Dict

# Load environment variables
load_dotenv()

class GitHubReplicator:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY")  # Format: "username/repo"
        
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found in environment variables")
        if not self.repo:
            raise ValueError("GITHUB_REPOSITORY not found in environment variables")
            
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = f"https://api.github.com/repos/{self.repo}"
        print(f"🔗 Repository: {self.repo}")
        print(f"🔗 API Base: {self.base_url}")

    def is_binary_file(self, filename: str) -> bool:
        """Check if file is binary and should be skipped"""
        binary_extensions = {
            '.pyc', '.pyo', '.pyd', '.exe', '.dll', '.so', '.dylib',
            '.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.tar', '.gz'
        }
        return any(filename.lower().endswith(ext) for ext in binary_extensions)

    def should_skip_file(self, filename: str) -> bool:
        """Check if file should be skipped"""
        skip_files = {
            '.gitignore', 'README.md', '.DS_Store', 'Thumbs.db',
            '.env', '.env.local', '.env.production'
        }
        skip_folders = {
            '__pycache__', '.git', 'node_modules', '.vscode', '.idea'
        }
        
        return (filename in skip_files or 
                any(folder in filename for folder in skip_folders) or
                self.is_binary_file(filename))

    def get_folder_contents(self, path: str) -> List[Dict]:
        """Get all files and folders in a directory"""
        url = f"{self.base_url}/contents/{path}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching {path}: {response.status_code}")
            if response.status_code == 404:
                print(f"  Path '{path}' not found in repository")
            return []

    def get_file_content(self, path: str) -> tuple[str, str, bool]:
        """Get content and SHA of a specific file"""
        url = f"{self.base_url}/contents/{path}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            file_data = response.json()
            try:
                # Try to decode as text
                content = base64.b64decode(file_data['content']).decode('utf-8')
                return content, file_data['sha'], False  # False = not binary
            except UnicodeDecodeError:
                # It's a binary file
                return file_data['content'], file_data['sha'], True  # True = binary
        else:
            print(f"Error fetching file {path}: {response.status_code}")
            return "", "", False

    def create_file(self, path: str, content: str, message: str, is_binary: bool = False):
        """Create a new file"""
        url = f"{self.base_url}/contents/{path}"
        
        if is_binary:
            # For binary files, content is already base64 encoded
            file_content = content
        else:
            # For text files, encode to base64
            file_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        data = {
            "message": message,
            "content": file_content
        }
        
        response = requests.put(url, json=data, headers=self.headers)
        
        if response.status_code == 201:
            print(f"✓ Created: {path}")
            return True
        else:
            print(f"✗ Error creating {path}: {response.status_code}")
            if response.status_code == 403:
                print(f"  Permission denied. Check if your token has 'repo' scope")
            elif response.status_code == 422:
                print(f"  File might already exist or invalid content")
            return False

    def update_content_references(self, content: str) -> str:
        """Update internal references from September to October"""
        replacements = {
            'nav_sep_25.py': 'nav_oct_25.py',
            'Nav_Sep_2025': 'Nav_Oct_2025',
            'September_2025': 'October_2025',
            'September': 'October',
            'september': 'october',
            'Sep': 'Oct',
            'sep': 'oct',
            '2025-09': '2025-10',
            '09/2025': '10/2025',
        }
        
        updated_content = content
        for old, new in replacements.items():
            updated_content = updated_content.replace(old, new)
        
        return updated_content

    def replicate_folder(self, source_folder: str, target_folder: str):
        """Replicate folder structure from source to target"""
        print(f"\n🚀 Starting replication: {source_folder} → {target_folder}")
        
        # Get all contents from source folder
        contents = self.get_folder_contents(source_folder)
        
        if not contents:
            print(f"❌ No contents found in {source_folder}")
            return
        
        success_count = 0
        total_count = 0
        
        for item in contents:
            # Skip unwanted files/folders
            if self.should_skip_file(item['name']):
                print(f"⏭️  Skipping: {item['name']}")
                continue
                
            total_count += 1
            
            if item['type'] == 'file':
                # Process file
                source_path = item['path']
                target_path = source_path.replace(source_folder, target_folder)
                
                print(f"📄 Processing: {source_path}")
                
                # Get file content
                content, sha, is_binary = self.get_file_content(source_path)
                
                if content:
                    if not is_binary:
                        # Update content references for text files
                        updated_content = self.update_content_references(content)
                    else:
                        # Keep binary content as-is
                        updated_content = content
                    
                    # Create new file
                    if self.create_file(
                        target_path, 
                        updated_content, 
                        f"chore: replicate {source_folder} structure for {target_folder}",
                        is_binary
                    ):
                        success_count += 1
                        
            elif item['type'] == 'dir':
                # Recursively process subdirectories
                print(f"📁 Processing directory: {item['path']}")
                self.replicate_folder(
                    item['path'], 
                    item['path'].replace(source_folder, target_folder)
                )
        
        print(f"\n✅ Completed: {success_count}/{total_count} files processed successfully")

def main():
    try:
        replicator = GitHubReplicator()
        
        print("\n🚀 Starting replication of root files to October_2025 folder...")
        
        # Get all files and folders from root
        contents = replicator.get_folder_contents("")  # Empty string for root
        
        if not contents:
            print("❌ No contents found in repository root")
            return
        
        # Create October_2025 folder by replicating each file
        success_count = 0
        total_count = 0
        
        for item in contents:
            # Skip unwanted files/folders
            if replicator.should_skip_file(item['name']):
                print(f"⏭️  Skipping: {item['name']}")
                continue
                
            total_count += 1
            
            if item['type'] == 'file':
                source_path = item['name']
                target_path = f"October_2025/{source_path}"
                
                print(f"📄 Replicating: {source_path} → {target_path}")
                
                # Get file content
                content, sha, is_binary = replicator.get_file_content(source_path)
                
                if content:
                    if not is_binary:
                        # Update content references for text files
                        updated_content = replicator.update_content_references(content)
                    else:
                        # Keep binary content as-is
                        updated_content = content
                    
                    # Create new file in October_2025 folder
                    if replicator.create_file(
                        target_path, 
                        updated_content, 
                        "chore: replicate Nav_Sep_2025 structure for October_2025",
                        is_binary
                    ):
                        success_count += 1
                        
            elif item['type'] == 'dir':
                # Skip unwanted directories
                if not replicator.should_skip_file(item['name']):
                    # Replicate entire folders
                    source_folder = item['name']
                    target_folder = f"October_2025/{source_folder}"
                    
                    print(f"📁 Replicating folder: {source_folder} → {target_folder}")
                    replicator.replicate_folder(source_folder, target_folder)
        
        print(f"\n✅ Completed: Successfully replicated repository structure to October_2025/")
        print(f"📊 Files processed: {success_count}/{total_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()