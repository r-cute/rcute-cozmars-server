import setuptools

with open("./README.md", 'r') as f:
    long_description = f.read()

with open('./requirements.txt', 'r') as f:
    requirements = [a.strip() for a in f]

setuptools.setup(
    name="rcute-cozmars-server",
    version="1.0.1",
    author="Huang Yan",
    author_email="hyansuper@foxmail.com",
    description="Firmware for Cozmars, the 3d printable educational robot.",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hyansuper/rcute-cozmars-server",
    packages=['rcute_cozmars_server'],
    install_requires=requirements,
    include_package_data=True,
    classifiers=(
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    # entry_points={
    #       'console_scripts': [
    #           'rcute_cozmars_server = rcute_cozmars_server.__main__:main'
    #       ]
    # },

)