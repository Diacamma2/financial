# -*- coding: utf-8 -*-
'''
setup module to pip integration of Diacamma accounting

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''


from setuptools import setup
from diacamma.accounting import __version__

setup(
    name="diacamma-financial",
    version=__version__,
    author="Lucterios",
    author_email="info@diacamma.org",
    url="http://www.diacamma.org",
    description="Diacamma financial modules for Lucterios framework.",
    long_description="""
    Diacamma financial modules for Lucterios framework.
    """,
    include_package_data=True,
    platforms=('Any',),
    license="GNU General Public License v3",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django :: 3.0',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Natural Language :: French',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Database :: Front-Ends',
        'Topic :: Office/Business :: Financial :: Accounting',
    ],
    packages=["diacamma", "diacamma.accounting", "diacamma.invoice", "diacamma.payoff"],
    package_data={
        "diacamma.accounting.migrations": ['*'],
        "diacamma.accounting.system": ['*', 'locale/*/*/*'],
        "diacamma.accounting": ['build', 'images/*', 'locale/*/*/*', 'help/*'],
        "diacamma.invoice.migrations": ['*'],
        "diacamma.invoice": ['build', 'images/*', 'locale/*/*/*', 'help/*'],
        "diacamma.payoff.migrations": ['*'],
        "diacamma.payoff": ['build', 'images/*', 'locale/*/*/*', 'help/*'],
    },
    install_requires=["lucterios ~=2.6", "lucterios-contacts ~=2.6", "requests"],
)
