from SPARQLWrapper import SPARQLWrapper, JSON

class DbpediaService:
    def __init__(self):
        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        self.sparql.setReturnFormat(JSON)

    def get_enriched_data_bulk(self, uri_list):
        if not uri_list:
            return {}

        formatted_uris = " ".join([f"<{uri}>" for uri in uri_list])

        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT ?uri ?abstract ?image
        WHERE {{
            VALUES ?uri {{ {formatted_uris} }}
            ?uri dbo:abstract ?abstract .
            OPTIONAL {{ ?uri dbo:thumbnail ?image }}
            FILTER (LANG(?abstract) = 'fr')
        }}
        """

        self.sparql.setQuery(query)
        
        try:
            results = self.sparql.query().convert()
            
            enriched_data = {}
            for result in results["results"]["bindings"]:
                uri = result["uri"]["value"]
                enriched_data[uri] = {
                    "description": result["abstract"]["value"],
                    "image": result.get("image", {}).get("value", None)
                }
            return enriched_data

        except Exception as e:
            print(f"Error querying DBpedia: {e}")
            return {}
