from azure.cosmos import CosmosClient ,PartitionKey


def connect_azure(url:str ,key:str , database_name:str ,container_name: str ,partition_key_path :str = None):
    """
    Connects to Azure Cosmos DB and ensures the specified database and container exist.

    Args:
        url (str): The endpoint URL of the Azure Cosmos DB account.
        key (str): The primary or secondary access key for authentication.
        database_name (str): The name of the database to connect to or create.
        container_name (str): The name of the container to connect to or create.
        partition_key_path (str, optional): The partition key path for the container (e.g., '/id'). 
                                             If None, it fetches an existing container client without creating a new one.

    Returns:
        ContainerProxy or str: The Cosmos DB container client object, or an error message if missing.
    """
    try:
        client=CosmosClient(url,credential=key)

        database= client.create_database_if_not_exists(id=database_name)

        if partition_key_path:
            container=database.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path=partition_key_path),
                offer_throughput=400
            )
        else:
            try:
                container =database.get_container_client(container_name)
                container.read()
            except:
                raise ValueError(
                    f"Container '{container_name}' does not exist. Please provide 'partition_key_path' to create it."

                )

        return container
        
    except Exception as e:
        return ValueError(
             f"ERROR OCCURD !!   {e}"
        )
    
    

