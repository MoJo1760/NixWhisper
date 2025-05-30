from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

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
    install_requires=[
        "torch>=2.0.0",
        "torchaudio>=2.0.0",
        "faster-whisper>=0.9.0",
        "numpy>=1.24.0",
        "sounddevice>=0.4.6",
        "pynput>=1.7.6",
        "pyperclip>=1.8.2",
        "python-xlib>=0.33; sys_platform == 'linux'",
        "PyGObject>=3.42.0",
        "pycairo>=1.23.0",
    ],
    entry_points={
        "console_scripts": [
            "nixwhisper=nixwhisper.main:main",
        ],
    },
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
)
