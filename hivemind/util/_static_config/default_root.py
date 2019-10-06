"""
Root Node For {_hive_name}
"""
import functools


from hivemind import RootController

class {_hive_name|cap}Controller(RootController):
    pass

if __name__ == '__main__':
    {_hive_name|cap}Controller.exec_(logging='verbose')
