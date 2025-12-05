from setuptools import setup, find_packages

setup(
    name="coimealta",
    version="0.0.14",
    description="A keeper for information about inventory and contacts.",
    long_description="""
    A keeper for information about inventory and contacts.

    The inventory uses CSV files to track books and general
    posessions, and storage locations for both, with storage locations
    being nested hierarchally, for example a box on a shelf in a room.

    The contacts system uses CSV files for your contacts list, and has
    columns for many things including who is related to whom.  It
    should in principle be a suitable basis for a Christmas card
    address list generator.""",
    author="John C. G. Sturdy",
    author_email="jcg.sturdy@gmail.com",
    packages=find_packages(),
    install_requires=[
        "python-decouple"
    ],
)
