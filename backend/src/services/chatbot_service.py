import os
import pickle
from sentence_transformers import SentenceTransformer, util
import torch
from google import genai

class ChatBotService:
    def __init__(self, graph, api_key, cache_file="search_index.pkl"):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.graph = graph
        self.documents = []
        self.metadata = []
        self.embeddings = None
        self.cache_file = cache_file
        
        self.client = genai.Client(api_key=api_key)

        self._build_index()

    def _build_index(self):
        if os.path.exists(self.cache_file):
            print(f"Loading index from {self.cache_file}...")
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.metadata = data['metadata']
                self.embeddings = data['embeddings']
            return

        query = "SELECT DISTINCT ?s WHERE { ?s ?p ?o }"
        subjects = self.graph.query(query)
        
        temp_docs = []
        temp_meta = []

        for row in subjects:
            subject_uri = row['s']
            prop_query = "SELECT ?p ?o WHERE { ?s ?p ?o }"
            properties = self.graph.query(prop_query, initBindings={'s': subject_uri})
            
            context_parts = []
            entity_label = str(subject_uri).split('/')[-1]
            
            for prop in properties:
                pred = str(prop['p']).split('/')[-1].split('#')[-1]
                obj = str(prop['o'])
                context_parts.append(f"{pred} is {obj}")
                if pred.lower() in ['label', 'name']:
                    entity_label = obj

            full_text = f"Entity: {entity_label}. " + ". ".join(context_parts)
            temp_docs.append(full_text)
            temp_meta.append({'uri': str(subject_uri), 'label': entity_label, 'context': full_text})

        self.documents = temp_docs
        self.metadata = temp_meta

        if self.documents:
            self.embeddings = self.model.encode(self.documents, convert_to_tensor=True)

        with open(self.cache_file, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'metadata': self.metadata,
                'embeddings': self.embeddings
            }, f)

    def search(self, user_query, top_k=3):
        if self.embeddings is None or not self.documents:
            return []

        query_embedding = self.model.encode(user_query, convert_to_tensor=True)
        if self.embeddings.device != query_embedding.device:
            query_embedding = query_embedding.to(self.embeddings.device)
            
        scores = util.cos_sim(query_embedding, self.embeddings)[0]
        top_results = torch.topk(scores, k=min(top_k, len(self.documents)))

        results = []
        for score, idx in zip(top_results.values, top_results.indices):
            idx = int(idx)
            results.append(self.metadata[idx])
            
        return results

    def ask_gemini(self, user_query):
        retrieved_docs = self.search(user_query)
        context_str = "\n".join([doc['context'] for doc in retrieved_docs])

        prompt = f"""
        You are an assistant for a Cycling Tour Operator. 
        Answer the question based strictly on the context below.

        Context:
        {context_str}

        Question: {user_query}
        """
        
        response = self.client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt
        )
        return response.text
