import os
import subprocess
import sys
from pathlib import Path
from setuptools import setup, find_packages, Command
from setuptools.command.install import install

# Custom command to download the model after installation
class DownloadModelCommand(install):
    """Custom command to download the Whisper model after installation."""
    
    def run(self):
        # Run the standard install first
        install.run(self)
        
        # Get the site-packages directory
        import site
        if hasattr(site, 'getsitepackages'):
            site_packages = site.getsitepackages()[0]
        else:
            # For virtualenv/venv
            site_packages = site.getusersitepackages()
            
        # Path to the installed package's models directory
        models_dir = os.path.join(site_packages, 'nixwhisper', 'models', 'base.en')
        
        # Skip if the model already exists
        if os.path.exists(models_dir) and any(os.scandir(models_dir)):
            print(f"Model already exists at {models_dir}, skipping download.")
            return
            
        print(f"Downloading Whisper model to {models_dir}...")
        
        # Ensure the directory exists
        os.makedirs(models_dir, exist_ok=True)
        
        # Download the model using the download script
        try:
            subprocess.check_call([
                sys.executable,
                '-c',
                'from faster_whisper import WhisperModel; '
                f'WhisperModel("base.en", device="cpu", download_root="{os.path.dirname(models_dir)}")'
            ])
            print("Successfully downloaded the Whisper model!")
        except Exception as e:
            print(f"Error downloading the model: {e}")
            print("You can download it later by running: nixwhisper-download-model")

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements from requirements.txt
def read_requirements():
    with open('requirements.txt') as f:
        return [line.strip() for line in f 
                if line.strip() 
                and not line.startswith('#')]

# Find all packages
packages = find_packages(where="src")

# Package data
package_data = {
    "nixwhisper": [
        "*.ui", "*.glade", "*.css", "*.desktop", "*.svg", "*.png",
        "models/base.en/*"
    ],
    "nixwhisper.scripts": ["*.py"],
}

# Entry points
entry_points = {
    "console_scripts": [
        "nixwhisper=nixwhisper.__main__:main",
        "nixwhisper-download-model=nixwhisper.scripts.download_model:main",
    ],
}

# Data files
data_files = [
    ('share/applications', ['data/nixwhisper.desktop']),
    ('share/icons/hicolor/scalable/apps', ['data/icons/hicolor/scalable/apps/nixwhisper.svg']),
    ('share/nixwhisper', ['data/config.json']),
]

setup(
    name="nixwhisper",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A privacy-focused, offline speech-to-text dictation system for Linux",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/nixwhisper",
    package_dir={"": "src"},
    packages=packages,
    package_data=package_data,
    data_files=data_files,
    python_requires=">=3.8",
    install_requires=[
        'torch>=2.0.0',
        'torchaudio>=2.0.0',
        'faster-whisper>=0.9.0',
        'numpy>=1.24.0',
        'pynput>=1.7.6',
        'pyperclip>=1.8.2',
        'python-xlib>=0.33; sys_platform == "linux"',
        'pydantic>=2.0.0,<3.0.0',
        'click>=8.1.0',
        'pydub>=0.25.1',
        'soundfile>=0.12.1',
    ],
    extras_require={
        'gui': [
            'PyQt6>=6.4.0',
        ],
    },
    entry_points=entry_points,
    cmdclass={},
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Utilities",
    ],
    keywords="speech-to-text dictation whisper offline linux",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/nixwhisper/issues",
        "Source": "https://github.com/yourusername/nixwhisper",
    },
)
