# Logging handler for SQLite
# Based on
#   https://stackoverflow.com/questions/2314307/python-logging-to-database
#   https://docs.python.org/3/library/logging.html#handlers
#   https://gist.github.com/ykessler/2662203#file_sqlite_handler.py
#
# python SQLiteHandler.py


import sqlite3
import logging
import pandas as pd

class SQLiteHandler(logging.Handler):
    '''
    Logging handler for SQLite

    Based on Yarin Kessler's sqlite_handler.py https://gist.github.com/ykessler/2662203#file_sqlite_handler.py
    '''  
    def __init__(self, database, table, attributes_list):
        '''
        SQLiteHandler class constructor

        Parameters:
            self: instance of the class
            database: database
            table: log table name
            attributes_list: log table columns

        Returns:
            None
        '''
        DEFAULT_DATA_TYPE = 'TEXT'
        #super(SQLiteHandler, self).__init__() # for python 2.X
        super().__init__() # for python 3.X
        self.database = database
        self.table = table
        self.attributes = attributes_list

        # Create table if needed
        create_table_sql = 'CREATE TABLE IF NOT EXISTS ' + self.table + ' (' + ((' ' + DEFAULT_DATA_TYPE + ', ').join(self.attributes)) + ' ' + DEFAULT_DATA_TYPE + ');'
        #print(create_table_sql)
        conn = sqlite3.connect(self.database)
        conn.execute(create_table_sql)
        conn.commit()
        conn.close()


    def emit(self, record):
        '''
        Save the log record

        Parameters:
            self: instance of the class
            record: log record to be saved

        Returns:
            None
        '''
        # Use default formatting if no formatter is set
        self.format(record)

        #print(record.__dict__)
        record_values = [record.__dict__[k] for k in self.attributes]
        str_record_values = ', '.join("'{0}'".format(v.replace("'", '').replace('"', '').replace('\n', ' ')) for v in record_values)
        #print(str_record_values)

        insert_sql = 'INSERT INTO ' + self.table + ' (' + (', '.join(self.attributes)) + ') VALUES (' + str_record_values + ');'
        #print(insert_sql)
        conn = sqlite3.connect(self.database)
        conn.execute(insert_sql)
        conn.commit()
        conn.close()