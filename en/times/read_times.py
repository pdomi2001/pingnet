import sqlite3
import pandas as pd
import os 

def read_sqlite(db_file):
    with sqlite3.connect(db_file) as conn:
        df = pd.read_sql_query("SELECT * FROM tempi", conn)
    return df

def main():
    #get the path of the database file
    db_file=os.path.join(os.path.dirname(__file__),'tempi.db')
    sqlite_df = read_sqlite(db_file)
    json_df=pd.read_json("tempi.json")
    html_df=pd.read_html("tempi.html")
    xlsx_df=pd.read_excel("tempi.xlsx")
    print("tempi.db(sqlite):",sqlite_df)
    print("tempi.csv:",pd.read_csv("tempi.csv"))
    print("tempi.json:",json_df)
    print("tempi.html:",html_df)
    print("tempi.xmls(excel):",xlsx_df)

if __name__=='__main__':
    main()
