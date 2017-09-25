from setuptools import setup, find_packages

setup(
    name='hieronymus',
    version='0.1.0',
    author='Enstaved',
    author_email='admin@enstaved.com',
    description='Enstaved Staff Rendering Service.',
    long_description=open('README.md').read(),
    license='LICENSE.txt',
    packages=find_packages(),
    url='https://hieronymus.enstaved.com',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'hieronymus = hieronymus.hieronymus:main',
        ]
    },
    install_requires=[
        'solidpython>=0.2,<0.3',
        'Flask>=0.12.2,<0.13',
        'Flask-Env>=1.0.1,<2.0',
        'Flask-Cors>=3.0.3,<4.0',
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
    ],
)
