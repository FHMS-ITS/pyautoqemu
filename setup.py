from setuptools import setup

setup(name='pyautoqemu',
      version='0.1',
      description='A Python package for automating user actions on qemu virtual machines using computer vision and HID input.',
      url='https://wiwi-gitlab.uni-muenster.de/itsecurity/pyautoqemu',
      author_email='lukas.schmidt@wi.uni-muenster.de',
      packages=['pyautoqemu'],
      scripts=['pyautoqemu/launch.sh']
      )
