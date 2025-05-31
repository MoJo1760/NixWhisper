from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements from requirements.txt
def read_requirements():
    with open('requirements.txt') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="nixwhisper",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A privacy-focused, offline speech-to-text dictation system for Linux",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/nixwhisper",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "nixwhisper=nixwhisper.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "nixwhisper": ["*.ui", "*.glade", "*.css", "*.desktop", "*.svg", "*.png"],
    },
    data_files=[
        ('share/applications', ['data/nixwhisper.desktop']),
        ('share/icons/hicolor/scalable/apps', ['data/icons/hicolor/scalable/apps/nixwhisper.svg']),
        ('share/nixwhisper', ['data/config.json']),
    ],
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
