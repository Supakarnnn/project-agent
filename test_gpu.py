from langchain_community.embeddings import DeepInfraEmbeddings

embeddings = DeepInfraEmbeddings(
    deepinfra_api_token="YjajcsocLmayK43rerA5tHJfRwXbHz2Y",
    model_id="BAAI/bge-m3",
    normalize=True
)
