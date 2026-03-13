import os
import unittest
from unittest.mock import patch

from aiops.config import Settings
from aiops.knowledge.vector_store import VectorStoreManager


class TestVectorStoreSettingsStage2Task1(unittest.TestCase):
    def setUp(self) -> None:
        self._env_backup = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)

    @patch("aiops.knowledge.vector_store.Chroma")
    @patch("aiops.knowledge.vector_store.SafeLiteLLMEmbeddings")
    def test_reads_from_settings(self, mock_embeddings_cls, mock_chroma_cls) -> None:
        settings = Settings.model_validate(
            {
                "knowledge": {
                    "embeddings": {
                        "model": "ollama/test-embed",
                        "api_key": "k1",
                        "api_base": "http://embed.local",
                    },
                    "vector_store": {
                        "persist_directory": "./vs_dir",
                        "collection_name": "kb_test",
                    },
                }
            }
        )

        VectorStoreManager(settings=settings)

        mock_embeddings_cls.assert_called_once_with(
            model="ollama/test-embed",
            api_base="http://embed.local",
            api_key="k1",
        )

        chroma_kwargs = mock_chroma_cls.call_args.kwargs
        self.assertEqual(chroma_kwargs["persist_directory"], "./vs_dir")
        self.assertEqual(chroma_kwargs["collection_name"], "kb_test")

    @patch("aiops.knowledge.vector_store.Chroma")
    @patch("aiops.knowledge.vector_store.SafeLiteLLMEmbeddings")
    def test_falls_back_to_litellm_env(self, mock_embeddings_cls, mock_chroma_cls) -> None:
        os.environ["LITELLM_EMBEDDING_MODEL"] = "ollama/env-embed"
        os.environ["LITELLM_EMBEDDING_API_KEY"] = "k_env"
        os.environ["LITELLM_EMBEDDING_API_BASE"] = "http://env.local"

        settings = Settings.model_validate({"knowledge": {"embeddings": {}}})
        VectorStoreManager(settings=settings)

        mock_embeddings_cls.assert_called_once_with(
            model="ollama/env-embed",
            api_base="http://env.local",
            api_key="k_env",
        )

        chroma_kwargs = mock_chroma_cls.call_args.kwargs
        self.assertEqual(chroma_kwargs["persist_directory"], "./chroma_db")
        self.assertEqual(chroma_kwargs["collection_name"], "knowledge_base")

    @patch("aiops.knowledge.vector_store.Chroma")
    @patch("aiops.knowledge.vector_store.SafeLiteLLMEmbeddings")
    def test_prefers_explicit_args(self, mock_embeddings_cls, mock_chroma_cls) -> None:
        settings = Settings.model_validate(
            {
                "knowledge": {
                    "embeddings": {
                        "model": "ollama/settings-embed",
                        "api_key": "k_settings",
                        "api_base": "http://settings.local",
                    },
                    "vector_store": {
                        "persist_directory": "./dir_settings",
                        "collection_name": "col_settings",
                    },
                }
            }
        )

        VectorStoreManager(
            persist_directory="./dir_explicit",
            collection_name="col_explicit",
            embedding_model="ollama/explicit-embed",
            api_key="k_explicit",
            api_base="http://explicit.local",
            settings=settings,
        )

        mock_embeddings_cls.assert_called_once_with(
            model="ollama/explicit-embed",
            api_base="http://explicit.local",
            api_key="k_explicit",
        )

        chroma_kwargs = mock_chroma_cls.call_args.kwargs
        self.assertEqual(chroma_kwargs["persist_directory"], "./dir_explicit")
        self.assertEqual(chroma_kwargs["collection_name"], "col_explicit")


if __name__ == "__main__":
    unittest.main(verbosity=2)

