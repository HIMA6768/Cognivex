import pandas as pd
from azure_connection import connect_azure
import os
from dotenv import load_dotenv
load_dotenv()
connectionsuccess=False

# assigning cosmosdb env variables
url=os.getenv("URL")
key=os.getenv("KEY")
database=os.getenv("database")
container=os.getenv("container")

# assigning  partition key
partitionkeypath=""
# load data 
data1=pd.read_csv(r"C:\Users\HIMADRI\Desktop\COGNIZANT\classification_dataset\test_dataset_C.csv")
data2=pd.read_csv(r"C:\Users\HIMADRI\Desktop\COGNIZANT\classification_dataset\validation_dataset _C.csv")

data=pd.concat([data1,data2],axis=0)

# checking if patient id is primary or not 
# print(data.shape[0])
# print(len(data["patient_id"].unique()))

# reassigning partion key
partitionkeypath="/"+str(data.columns[0])


# connecting to cloud
connection=connect_azure(url=url,key=key,database_name=database,container_name=container,partition_key_path=partitionkeypath)
if type(connection)is not ValueError:
   connectionsuccess=True
if connectionsuccess:
    print("connected with azure cosmos db  successfully ")
    # inserting data into container
    data.drop(["pam50_+_claudin-low_subtype"],axis=1,inplace=True)
    data=data.to_dict(orient="records")
    try:
        for item in data:
            item["id"]=str(item["patient_id"])
            connection.create_item(item)
        print("data inserted successfully")
    except Exception as e:
        print(ValueError(f"ERROR = {e}")) 
   