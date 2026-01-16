from time import time
from google import genai
from google.genai import types
from .data_summary import get_rdf_data_summary
from .prompt import get_sparql_prompt


class TextToSparqlService:
    def __init__(self, graph, schema_content, api_key):
        self.client = genai.Client(api_key=api_key)
        self.graph = graph
        self.schema_content = schema_content

    def text_to_sparql(self, text_query):
        data_summary = get_rdf_data_summary(self.graph)
        prompt = get_sparql_prompt(self.schema_content, data_summary, text_query)
        sparql_query = self.call_gemini_api(prompt)
        return sparql_query

    def call_gemini_api(self, prompt, model="gemini-2.5-flash-lite", temperature=0.0):
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=temperature),
            )
            return response.text
        except Exception as e:
            return f"An error occurred: {e}"
