import setuptools
import os

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'rcute_cozmars_server', 'version.py')) as f:
    ns = {}
    exec(f.read(), ns)
    version = ns['__version__']

description=f"R-Cute 教育机器人 Cozmars 固件，最新版本 {version}"

with open('./requirements.txt', 'r') as f:
    requirements = [a.strip() for a in f]

setuptools.setup(
    name="rcute-cozmars-server",
    version=version,
    author="Huang Yan",
    author_email="hyansuper@foxmail.com",
    #license="MIT",
    description=description,
    long_description=f"#rcute-cozmars-server\n\n{description}",
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