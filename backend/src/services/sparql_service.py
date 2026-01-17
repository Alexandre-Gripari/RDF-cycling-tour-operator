from rdflib import Graph


class SparqlService:
    def __init__(self, ttl_files):
        self.graph = Graph()
        self._load_ttl_files(ttl_files)

    def _load_ttl_files(self, ttl_files):
        for ttl_file in ttl_files:
            try:
                self.graph.parse(ttl_file, format="turtle")
                print(f"Loaded {ttl_file} successfully.")
            except Exception as e:
                print(f"Error loading {ttl_file}: {e}")

    def execute_query(self, query):
        try:
            results = self.graph.query(query)
            return [{str(var): str(row[var]) for var in row.labels} for row in results]
        except Exception as e:
            raise Exception(f"Error executing query: {e}")

    def get_graph(self):
        return self.graph
    
    def predict_recommendations(self, client_uri):        
        return { "tour_uri": "tour_uri", "score": 0.95, "reason": "Based on similar clients" } 
