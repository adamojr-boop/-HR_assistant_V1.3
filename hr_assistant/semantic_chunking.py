import numpy as np
from langchain_openai import OpenAIEmbeddings
from hr_assistant.config import OPENAI_API_KEY

class SemanticChunking:
    
    def calculate_cosine_distances(self, sentences):
        """Calcola le distanze del coseno tra le frasi combinate usando solo numpy."""
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        combined_texts = [s["combined_sentence"] for s in sentences]
        
        try:
            vectors = embeddings.embed_documents(combined_texts)
        except Exception as e:
            print(f"[DEBUG] Errore negli embedding: {e}")
            return []

        distances = []
        for i in range(len(vectors) - 1):
            v1 = np.array(vectors[i])
            v2 = np.array(vectors[i+1])
            
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            if norm_v1 == 0 or norm_v2 == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (norm_v1 * norm_v2)
                
            distances.append(1 - similarity)
            
        return distances

    def combine_sentences(self, sentences, buffer_size=1):
        """Aggiunge un buffer di frasi attorno a ciascuna frase per arricchire il contesto."""
        for i, sentence_obj in enumerate(sentences):
            combined_text = ""
            for j in range(i - buffer_size, i + buffer_size + 1):
                if 0 <= j < len(sentences):
                    combined_text += sentences[j]["sentence"] + ". "
            sentence_obj["combined_sentence"] = combined_text.strip()
        return sentences

    @staticmethod
    def chunk_it(txt: str) -> list[str]:
        """Suddivide il testo in chunk basandosi sulla distanza semantica (metodo principale)."""
        if not txt or not txt.strip():
            return []
        
        raw_sentences = [s.strip() for s in txt.replace("\n", " ").split(".") if s.strip()]
        if not raw_sentences:
            return [txt]

        sentences = [{"sentence": s} for s in raw_sentences]
        
        chunker = SemanticChunking()
        sentences = chunker.combine_sentences(sentences, buffer_size=1)
        distances = chunker.calculate_cosine_distances(sentences)
        
        if not distances:
            return [txt]

        breakpoint_threshold = np.percentile(distances, 85)

        chunks = []
        current_chunk = [sentences[0]["sentence"]]

        for i, dist in enumerate(distances):
            if dist > breakpoint_threshold:
                chunks.append(". ".join(current_chunk) + ".")
                current_chunk = [sentences[i+1]["sentence"]]
            else:
                current_chunk.append(sentences[i+1]["sentence"])

        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")

        return chunks

SemanticChunkerProcessor = SemanticChunking