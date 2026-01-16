from SPARQLWrapper import SPARQLWrapper, JSON
from urllib.parse import unquote
import sys

class DbpediaService:
    def __init__(self):
        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        self.sparql.setReturnFormat(JSON)
        self.sparql.addCustomHttpHeader("User-Agent", "Cycling Tour Operator")

        self.FIELD_CONFIG = {
            'image': {
                'var': '?image',
                'pred': 'dbo:thumbnail',
                'extra': '' 
            },
            'description': {
                'var': '?description',
                'pred': 'dbo:abstract',
                'extra': "FILTER (LANG(?description) = 'fr')" 
            },
            'website': {
                'var': '?website',
                'pred': 'dbo:wikiPageExternalLink',
                'extra': ''
            }
        }

    def get_enriched_data_bulk(self, uri_list, fields=None):
        if not uri_list:
            return {}

        if fields is None:
            fields = ['image']

        formatted_uris = " ".join([f"<{unquote(uri)}>" for uri in uri_list])

        select_vars = ["?uri"]
        where_clauses = []

        for field in fields:
            if field in self.FIELD_CONFIG:
                config = self.FIELD_CONFIG[field]
                
                select_vars.append(config['var'])
                
                clause = f"""
                OPTIONAL {{ 
                    ?uri {config['pred']} {config['var']} . 
                    {config['extra']} 
                }}"""
                where_clauses.append(clause)

        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT {' '.join(select_vars)}
        WHERE {{
            VALUES ?uri {{ {formatted_uris} }}
            {''.join(where_clauses)}
        }}
        """

        self.sparql.setQuery(query)
        
        try:
            results = self.sparql.query().convert()
            
            enriched_data = {}
            for result in results["results"]["bindings"]:
                uri = result["uri"]["value"]
                
                if uri not in enriched_data:
                    enriched_data[uri] = {}

                for field in fields:
                    if field in self.FIELD_CONFIG:
                        var_name = self.FIELD_CONFIG[field]['var'].lstrip('?')
                        val = result.get(var_name, {}).get("value", None)
                        if val:
                            enriched_data[uri][field] = val
                            
            return enriched_data

        except Exception as e:
            print(f"Error querying DBpedia: {e}", file=sys.stderr)
            return {}
