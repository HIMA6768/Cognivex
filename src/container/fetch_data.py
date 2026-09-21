import pandas as pd
import streamlit as st
from .azure_connection import connect_azure
import os
from dotenv import load_dotenv
load_dotenv()
# assigning cosmosdb env variables
try:
    connect_url = st.secrets["URL"]
    connect_key = st.secrets["KEY"]
    connect_database = st.secrets["database"]
    connect_container = st.secrets["container"]
except:
    connect_url = os.getenv("URL")
    connect_key = os.getenv("KEY")
    connect_database = os.getenv("database")
    connect_container = os.getenv("container")


# fetch data by patient id
def fetch_data_by_id(id : str, url :str = connect_url , key :str =connect_key ,database :str=connect_database ,container:str =connect_container):
    """Fetches patient records from Cosmos DB by  ID.
       Argument :
       patient_id : int this is the patient id to search 

       Returns : data of the id  or exception error string 
    
    """
    try:
        connection=connect_azure(url=url,key=key,database_name=database,container_name=container)
        query="select * from c where c.id = @id"
        parameters=[{"name":"@id","value":id}]

        data=list(connection.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        return data
    except Exception as e :
        return(ValueError(f"ERROR : {e}"))
    

def fetch_all_id(url :str = connect_url , key :str =connect_key ,database :str=connect_database ,container:str =connect_container):
    """Fetches all patient_id .
           Argument :
           None
    
           Returns : list of  {id: id}  or exception error string 
        
    """
    try:
            connection=connect_azure(url=url,key=key,database_name=database,container_name=container)
            query="select c.id from c "
    
            data=list(connection.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
            return data
    except Exception as e :
        return(ValueError(f"ERROR : {e}"))


if __name__=="__main__":
    print(fetch_data_by_id("382"))
    print(fetch_all_id())