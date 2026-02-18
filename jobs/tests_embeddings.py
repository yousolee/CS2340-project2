from django.test import SimpleTestCase, override_settings

from jobs.recommendations.embeddings import (
    CohereEmbeddingProvider,
    LocalDeterministicEmbeddingProvider,
    get_embedding_provider,
)


class _FakeEmbedResponse:
    def __init__(self, embeddings):
        self.embeddings = embeddings


class _FakeCohereClient:
    def __init__(self, response: _FakeEmbedResponse):
        self._response = response
        self.calls = []

    def embed(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


class EmbeddingProviderTests(SimpleTestCase):
    @override_settings(
        RECOMMENDER_EMBEDDING_PROVIDER="cohere",
        RECOMMENDER_COHERE_API_KEY="",
        RECOMMENDER_EMBEDDING_DIM=64,
    )
    def test_provider_falls_back_to_local_without_api_key(self):
        provider = get_embedding_provider()
        self.assertIsInstance(provider, LocalDeterministicEmbeddingProvider)

    @override_settings(
        RECOMMENDER_EMBEDDING_PROVIDER="cohere",
        RECOMMENDER_COHERE_API_KEY="test-key",
        RECOMMENDER_COHERE_MODEL="embed-v4.0",
        RECOMMENDER_COHERE_INPUT_TYPE="search_document",
        RECOMMENDER_EMBEDDING_DIM=16,
    )
    def test_provider_uses_cohere_when_configured(self):
        provider = get_embedding_provider()
        self.assertIsInstance(provider, CohereEmbeddingProvider)

    def test_cohere_provider_parses_v2_response(self):
        provider = CohereEmbeddingProvider(
            api_key="test-key",
            model="embed-v4.0",
            dim=4,
        )
        provider._client = _FakeCohereClient(
            _FakeEmbedResponse([[0.1, -0.2, 0.3, -0.4]])
        )

        vector = provider.embed("Backend engineering")

        self.assertEqual(len(vector), 4)
        self.assertAlmostEqual(sum(value * value for value in vector), 1.0, places=6)

    def test_cohere_provider_uses_local_fallback_on_bad_payload(self):
        provider = CohereEmbeddingProvider(
            api_key="test-key",
            model="embed-v4.0",
            dim=8,
        )
        provider._client = _FakeCohereClient(_FakeEmbedResponse([]))

        vector = provider.embed("Backend engineering")

        self.assertEqual(len(vector), 8)

    def test_cohere_provider_sends_v2_texts_payload(self):
        provider = CohereEmbeddingProvider(
            api_key="test-key",
            model="embed-v4.0",
            dim=4,
        )
        fake_client = _FakeCohereClient(
            _FakeEmbedResponse([[0.2, 0.1, -0.3, 0.4]])
        )
        provider._client = fake_client

        provider.embed("Backend engineering")

        self.assertEqual(len(fake_client.calls), 1)
        payload = fake_client.calls[0]
        self.assertEqual(payload["texts"], ["Backend engineering"])
        self.assertEqual(payload["model"], "embed-v4.0")
        self.assertEqual(payload["input_type"], "search_document")
