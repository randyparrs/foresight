# { "Depends": "py-genlayer:1j12s63yfjpva9ik2xgnffgrs6v44y1f52jvj9w7xvdn7qckd379" }

from genlayer import *


class TheSignal(gl.Contract):

    # --- Control ---
    owner: Address        # tu wallet — control total del contrato
    bot_address: Address  # wallet del bot — único que puede publicar

    # --- Counters ---
    article_counter: u256
    block_counter: u256

    # --- Storage: O(log n) per field access ---
    article_data: TreeMap[str, str]
    article_ids: DynArray[str]     # orden de publicación para get_latest
    category_index: DynArray[str]  # "CATEGORY:id" para filtrar por categoría

    def __init__(self):
        self.owner = gl.message.sender_address
        self.bot_address = gl.message.sender_address  # owner llama set_bot() después del deploy
        self.article_counter = u256(0)
        self.block_counter = u256(0)

    # ─── VIEW METHODS ───────────────────────────────────────────────────────────

    @gl.public.view
    def get_article(self, article_id: str) -> str:
        title = self._get(article_id, "title")
        if not title:
            return "Article not found"
        return (
            f"ID: {article_id} | "
            f"Title: {title} | "
            f"Category: {self._get(article_id, 'category')} | "
            f"Sentiment: {self._get(article_id, 'sentiment')} | "
            f"Headline: {self._get(article_id, 'headline')} | "
            f"Body: {self._get(article_id, 'body')} | "
            f"Tags: {self._get(article_id, 'tags')} | "
            f"Sources: {self._get(article_id, 'sources')} | "
            f"Block: {self._get(article_id, 'block')}"
        )

    @gl.public.view
    def get_article_count(self) -> u256:
        return self.article_counter

    @gl.public.view
    def get_articles_by_category(self, category: str) -> str:
        cat_upper = category.upper()
        ids = []
        for i in range(len(self.category_index)):
            entry = self.category_index[i]
            parts = entry.split(":", 1)
            if len(parts) == 2 and parts[0] == cat_upper:
                ids.append(parts[1])
        if not ids:
            return f"No articles found for category: {cat_upper}"
        return f"Category {cat_upper}: {len(ids)} article(s): {', '.join(ids[-20:])}"

    @gl.public.view
    def get_latest(self, count: u256) -> str:
        total = len(self.article_ids)
        if total == 0:
            return "No articles published yet"
        n = int(count)
        start = max(0, total - n)
        results = []
        for i in range(start, total):
            aid = self.article_ids[i]
            title = self._get(aid, "title")
            category = self._get(aid, "category")
            sentiment = self._get(aid, "sentiment")
            results.append(f"[{aid}] {category} | {sentiment} | {title}")
        return "\n".join(results)

    @gl.public.view
    def get_summary(self) -> str:
        total = len(self.article_ids)
        crypto = 0
        sports = 0
        politics = 0
        markets = 0
        tech = 0
        other = 0
        bullish = 0
        bearish = 0
        neutral = 0
        for i in range(total):
            aid = self.article_ids[i]
            cat = self._get(aid, "category")
            sent = self._get(aid, "sentiment")
            if cat == "CRYPTO":
                crypto += 1
            elif cat == "SPORTS":
                sports += 1
            elif cat == "POLITICS":
                politics += 1
            elif cat == "MARKETS":
                markets += 1
            elif cat == "TECH":
                tech += 1
            else:
                other += 1
            if sent in ("BULLISH", "POSITIVE"):
                bullish += 1
            elif sent in ("BEARISH", "NEGATIVE"):
                bearish += 1
            else:
                neutral += 1
        return (
            f"Foresight Journals\n"
            f"Total Articles: {total}\n"
            f"CRYPTO: {crypto} | SPORTS: {sports} | POLITICS: {politics} | "
            f"MARKETS: {markets} | TECH: {tech} | OTHER: {other}\n"
            f"Bullish/Positive: {bullish} | Bearish/Negative: {bearish} | Neutral: {neutral}"
        )

    @gl.public.view
    def get_bot(self) -> str:
        return str(self.bot_address)

    # ─── OWNER WRITE METHODS ────────────────────────────────────────────────────

    @gl.public.write
    def set_bot(self, new_bot: Address) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.owner).lower(), "Only owner can set bot address"
        self.bot_address = new_bot
        return f"Bot address updated to {str(new_bot)}"

    @gl.public.write
    def transfer_ownership(self, new_owner: Address) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.owner).lower(), "Only owner can transfer ownership"
        self.owner = new_owner
        return f"Ownership transferred to {str(new_owner)}"

    # ─── BOT WRITE METHODS ──────────────────────────────────────────────────────

    @gl.public.write
    def publish_article(
        self,
        category: str,
        source_url_1: str,
        source_url_2: str,
        source_url_3: str,
    ) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.bot_address).lower(), "Only the bot can publish articles"
        valid_categories = ("CRYPTO", "SPORTS", "POLITICS", "MARKETS", "TECH", "OTHER")
        assert category.upper() in valid_categories, "Invalid category"
        assert len(source_url_1) >= 10, "Source URL 1 too short"

        self.block_counter = u256(int(self.block_counter) + 1)
        article_id = str(int(self.article_counter))
        category = category.upper()

        def leader_fn():
            sources = []
            source_list = []
            for url in (source_url_1, source_url_2, source_url_3):
                if len(url) >= 10:
                    try:
                        raw = gl.nondet.web.render(url, mode="text")
                        sources.append(f"Source ({url}):\n{raw[:2000]}")
                        source_list.append(url)
                    except Exception:
                        sources.append(f"Source ({url}): Could not fetch content.")

            sources_text = "\n\n".join(sources)

            if category in ("CRYPTO", "MARKETS"):
                sentiment_options_temp = "BULLISH, BEARISH, or NEUTRAL"
            else:
                sentiment_options_temp = "POSITIVE, NEGATIVE, or NEUTRAL"

            if not source_list:
                # No sources could be fetched — generate article from topic context
                topic_context = " | ".join(
                    url for url in (source_url_1, source_url_2, source_url_3) if len(url) >= 10
                )
                fallback_prompt = f"""You are a professional financial and news journalist writing for Foresight Journals,
an AI-powered on-chain publication. Your writing is factual, concise, and insightful.

Category: {category}
The source URLs were not accessible. Topic references: {topic_context}

Based on your knowledge, write a complete, factual article about the most relevant topic
for the {category} category implied by these references.

Rules:
- Title: punchy, under 80 characters
- Headline: one sentence expanding on the title, under 150 characters
- Body: three focused paragraphs. Each paragraph is 2-3 sentences. Total body under 600 characters.
- Tags: 3 to 5 relevant keywords separated by commas
- Sentiment: {sentiment_options_temp}

Respond ONLY with this JSON:
{{
  "title": "Article title here",
  "headline": "One sentence headline expanding on the title",
  "body": "Paragraph one. Paragraph two. Paragraph three.",
  "tags": "tag1, tag2, tag3",
  "sentiment": "NEUTRAL"
}}
No extra text."""
                data = gl.nondet.exec_prompt(fallback_prompt, response_format="json")
                title = data.get("title", "Untitled")
                headline = data.get("headline", "")
                body = data.get("body", "")
                tags = data.get("tags", "")
                sentiment = data.get("sentiment", "NEUTRAL").upper()
                if category in ("CRYPTO", "MARKETS"):
                    valid_sentiments = ("BULLISH", "BEARISH", "NEUTRAL")
                else:
                    valid_sentiments = ("POSITIVE", "NEGATIVE", "NEUTRAL")
                if sentiment not in valid_sentiments:
                    sentiment = "NEUTRAL"
                return {
                    "title": title[:80],
                    "headline": headline[:150],
                    "body": body[:600],
                    "tags": tags,
                    "sentiment": sentiment,
                    "sources": ""
                }

            if category in ("CRYPTO", "MARKETS"):
                sentiment_options = "BULLISH, BEARISH, or NEUTRAL"
                sentiment_note = "BULLISH means positive outlook, BEARISH means negative outlook, NEUTRAL means mixed or unclear."
            else:
                sentiment_options = "POSITIVE, NEGATIVE, or NEUTRAL"
                sentiment_note = "POSITIVE means favorable news, NEGATIVE means unfavorable news, NEUTRAL means mixed."

            prompt = f"""You are a professional financial and news journalist writing for Foresight Journals,
an AI-powered on-chain publication. Your writing is factual, concise, and insightful.

Category: {category}
Sources provided:
{sources_text}

Write a well-structured news article based on the sources above.
The article must cover the most significant and newsworthy information from the sources.

Rules:
- Title: punchy, under 80 characters
- Headline: one sentence expanding on the title, under 150 characters
- Body: three focused paragraphs. Each paragraph is 2-3 sentences. Total body under 600 characters.
- Tags: 3 to 5 relevant keywords separated by commas
- Sentiment: {sentiment_options}
  {sentiment_note}

Respond ONLY with this JSON:
{{
  "title": "Article title here",
  "headline": "One sentence headline expanding on the title",
  "body": "Paragraph one. Paragraph two. Paragraph three.",
  "tags": "tag1, tag2, tag3",
  "sentiment": "BULLISH"
}}

sentiment must be exactly one of: {sentiment_options.replace(', or ', ', ')}.
No extra text."""

            data = gl.nondet.exec_prompt(prompt, response_format="json")

            title = data.get("title", "Untitled")
            headline = data.get("headline", "")
            body = data.get("body", "")
            tags = data.get("tags", "")
            sentiment = data.get("sentiment", "NEUTRAL").upper()

            if category in ("CRYPTO", "MARKETS"):
                valid_sentiments = ("BULLISH", "BEARISH", "NEUTRAL")
            else:
                valid_sentiments = ("POSITIVE", "NEGATIVE", "NEUTRAL")

            if sentiment not in valid_sentiments:
                sentiment = "NEUTRAL"

            title = title[:80]
            headline = headline[:150]
            body = body[:600]

            return {
                "title": title,
                "headline": headline,
                "body": body,
                "tags": tags,
                "sentiment": sentiment,
                "sources": ", ".join(source_list[:3])
            }

        def validator_fn(leaders_result) -> bool:
            if not isinstance(leaders_result, gl.vm.Return):
                return False
            try:
                validator_result = leader_fn()
                leader_data = leaders_result.calldata
                if leader_data["sentiment"] != validator_result["sentiment"]:
                    return False
                return True
            except Exception:
                return False

        data = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self._set(article_id, "title", data["title"])
        self._set(article_id, "headline", data["headline"])
        self._set(article_id, "body", data["body"])
        self._set(article_id, "tags", data["tags"])
        self._set(article_id, "sentiment", data["sentiment"])
        self._set(article_id, "sources", data["sources"])
        self._set(article_id, "category", category)
        self._set(article_id, "block", str(int(self.block_counter)))

        self.article_ids.append(article_id)
        self.category_index.append(f"{category}:{article_id}")
        self.article_counter = u256(int(self.article_counter) + 1)

        return (
            f"Article {article_id} published. "
            f"Category: {category}. "
            f"Sentiment: {data['sentiment']}. "
            f"Title: {data['title']}"
        )

    # ─── PRIVATE HELPERS ────────────────────────────────────────────────────────

    def _get(self, article_id: str, field: str) -> str:
        return str(self.article_data.get(f"{article_id}_{field}", ""))

    def _set(self, article_id: str, field: str, value: str) -> None:
        self.article_data[f"{article_id}_{field}"] = value
