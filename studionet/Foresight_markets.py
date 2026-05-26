# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

class ForesightMarkets(gl.Contract):

    # --- Owner ---
    owner: Address

    # --- Counters ---
    market_counter: u256
    block_counter: u256
    bettor_count: u256

    # --- Market storage: O(log n) per field access ---
    market_data: TreeMap[str, str]
    market_ids: DynArray[str]

    # --- Predictions history (DynArray — needed for full iteration) ---
    predictions: DynArray[str]

    # --- Claimed: O(log n) duplicate check ---
    claimed: TreeMap[str, u256]

    # --- Bettors: O(log n) duplicate check ---
    bettors_map: TreeMap[str, u256]

    # --- Source reputation: O(log n) access ---
    source_stats: TreeMap[str, str]

    def __init__(self):
        self.owner = gl.message.sender_address
        self.market_counter = u256(0)
        self.block_counter = u256(0)
        self.bettor_count = u256(0)

    # ── View functions ────────────────────────────────────────────────────────

    @gl.public.view
    def get_market(self, market_id: str) -> str:
        question = self._get(market_id, "question")
        if not question:
            return "Market not found"
        return (
            f"ID: {market_id} | "
            f"Question: {question} | "
            f"Category: {self._get(market_id, 'category')} | "
            f"Quality: {self._get(market_id, 'quality_score')}/10 | "
            f"Context: {self._get(market_id, 'context')} | "
            f"Status: {self._get(market_id, 'status')} | "
            f"Result: {self._get(market_id, 'result')} | "
            f"Confidence: {self._get(market_id, 'confidence')}% | "
            f"YES Pool: {self._format_gen(int(self._get(market_id, 'yes_pool') or '0'))} GEN | "
            f"NO Pool: {self._format_gen(int(self._get(market_id, 'no_pool') or '0'))} GEN | "
            f"Resolve Attempts: {self._get(market_id, 'resolve_attempts')} | "
            f"Reasoning: {self._get(market_id, 'reasoning')}"
        )

    @gl.public.view
    def get_market_count(self) -> u256:
        return self.market_counter

    @gl.public.view
    def get_my_predictions(self, user_address: str) -> str:
        my_preds = []
        for i in range(len(self.predictions)):
            entry = self.predictions[i]
            parts = entry.split(":")
            if len(parts) >= 4 and parts[1].lower() == str(user_address).lower():
                my_preds.append(
                    f"M{parts[0]}={parts[2]}({self._format_gen(int(parts[3]))} GEN)"
                )
        if not my_preds:
            return "No predictions found"
        return f"User has {len(my_preds)} prediction(s): " + " | ".join(my_preds[-20:])

    @gl.public.view
    def get_markets_by_category(self, category: str) -> str:
        cat_upper = category.upper()
        ids = []
        for i in range(len(self.market_ids)):
            mid = self.market_ids[i]
            if self._get(mid, "category") == cat_upper:
                ids.append(mid)
        if not ids:
            return f"No markets found for category: {cat_upper}"
        return f"Category {cat_upper}: {len(ids)} market(s): {', '.join(ids)}"

    @gl.public.view
    def get_source_reputation(self, url: str) -> str:
        data = str(self.source_stats.get(url[:50], ""))
        if not data:
            return "No reputation data for this source yet"
        parts = data.split(":")
        if len(parts) < 2:
            return "No reputation data for this source yet"
        correct = int(parts[0])
        total = int(parts[1])
        rate = (correct * 100) // total if total > 0 else 0
        return f"Source {url[:40]}... | Resolved: {correct}/{total} | Success Rate: {rate}%"

    @gl.public.view
    def get_summary(self) -> str:
        total = len(self.market_ids)
        open_markets = 0
        resolved = 0
        disputed = 0
        expired = 0
        for i in range(len(self.market_ids)):
            mid = self.market_ids[i]
            status = self._get(mid, "status")
            if status == "open":
                open_markets += 1
            elif status == "resolved":
                resolved += 1
            elif status == "disputed":
                disputed += 1
            elif status == "expired":
                expired += 1
        return (
            f"Foresight Markets\n"
            f"Total Markets: {total}\n"
            f"Open: {open_markets}\n"
            f"Resolved: {resolved}\n"
            f"Disputed: {disputed}\n"
            f"Expired: {expired}\n"
            f"Total Predictions: {len(self.predictions)}\n"
            f"Unique Predictors: {int(self.bettor_count)}"
        )

    @gl.public.view
    def get_bettor_count(self) -> u256:
        return self.bettor_count

    @gl.public.view
    def get_predictor_stats(self, user_address: str) -> str:
        addr = str(user_address).lower()
        wins = 0
        losses = 0
        total = 0
        for i in range(len(self.predictions)):
            entry = self.predictions[i]
            parts = entry.split(":")
            if len(parts) < 4 or parts[1].lower() != addr:
                continue
            total += 1
            market_id = parts[0]
            side = parts[2]
            status = self._get(market_id, "status")
            if status == "resolved":
                result = self._get(market_id, "result")
                if result in ("YES", "NO"):
                    if side == result:
                        wins += 1
                    else:
                        losses += 1
        if total == 0:
            return "Not a predictor yet"
        return f"{addr}={wins}W/{losses}L/{total}T"

    @gl.public.view
    def get_top_predictors(self) -> str:
        if int(self.bettor_count) == 0:
            return "No predictors yet"

        addrs = []
        wins_arr = []
        losses_arr = []
        total_arr = []

        for addr in self.bettors_map:
            addrs.append(addr)
            wins_arr.append(0)
            losses_arr.append(0)
            total_arr.append(0)

        for i in range(len(self.predictions)):
            entry = self.predictions[i]
            parts = entry.split(":")
            if len(parts) < 4:
                continue
            market_id = parts[0]
            addr = parts[1].lower()
            side = parts[2]

            idx = -1
            for j in range(len(addrs)):
                if addrs[j] == addr:
                    idx = j
                    break
            if idx == -1:
                continue

            total_arr[idx] = total_arr[idx] + 1
            status = self._get(market_id, "status")
            if status == "resolved":
                result = self._get(market_id, "result")
                if result in ("YES", "NO"):
                    if side == result:
                        wins_arr[idx] = wins_arr[idx] + 1
                    else:
                        losses_arr[idx] = losses_arr[idx] + 1

        order = list(range(len(addrs)))
        order.sort(key=lambda k: (-wins_arr[k], -total_arr[k]))

        parts_out = []
        limit = min(len(order), 50)
        for n in range(limit):
            k = order[n]
            parts_out.append(
                f"{addrs[k]}={wins_arr[k]}W/{losses_arr[k]}L/{total_arr[k]}T"
            )

        return f"Top predictors ({len(addrs)}): " + " | ".join(parts_out)

    # ── Owner-only write functions ─────────────────────────────────────────────

    @gl.public.write
    def generate_market(self, news_url: str, topic_hint: str) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.owner).lower(), "Only owner can create markets"
        assert len(news_url) >= 10, "News URL too short"
        assert len(topic_hint) >= 3, "Topic hint too short"

        self.block_counter = u256(int(self.block_counter) + 1)
        market_id = str(int(self.market_counter))

        def leader_fn():
            web_data = ""
            try:
                web_data = gl.nondet.web.render(news_url, mode="text")[:4000]
            except Exception:
                web_data = "Could not fetch news content."

            prompt = f"""You are an AI that creates prediction markets from news articles.
Read the news content below and identify ONE concrete future event that:
- Has a clear YES or NO outcome
- Can be verified by reading public news sources after it happens
- Is specific enough that reasonable people would agree on the outcome

Topic hint from the user: {topic_hint}

News content from {news_url}:
{web_data}

Create a prediction market for the most interesting verifiable event you found.
Then self-evaluate how verifiable and clear this market is on a scale of 1 to 10.
A score below 6 means the question is too vague or unverifiable.

Respond ONLY with this JSON:
{{
  "question": "Will X happen by date Y?",
  "category": "CRYPTO",
  "quality_score": 8,
  "reject": false,
  "reject_reason": "",
  "context": "one sentence explaining the event background"
}}

category must be exactly CRYPTO, SPORTS, POLITICS, TECH, or OTHER.
quality_score is an integer from 1 to 10.
reject must be true if quality_score is below 6, false otherwise.
question must be a clear YES or NO question under 120 characters.
No extra text."""

            data = gl.nondet.exec_prompt(prompt, response_format="json")

            question = data.get("question", "")
            category = data.get("category", "OTHER")
            quality_score = int(data.get("quality_score", 5))
            reject = data.get("reject", False)
            reject_reason = data.get("reject_reason", "")
            context = data.get("context", "")

            quality_score = max(1, min(10, quality_score))
            if category not in ("CRYPTO", "SPORTS", "POLITICS", "TECH", "OTHER"):
                category = "OTHER"
            if quality_score < 6:
                reject = True

            return {
                "question": question,
                "category": category,
                "quality_score": quality_score,
                "reject": reject,
                "reject_reason": reject_reason,
                "context": context,
            }

        def validator_fn(leaders_result) -> bool:
            if not isinstance(leaders_result, gl.vm.Return):
                return False
            try:
                validator_result = leader_fn()
                leader_data = leaders_result.calldata
                if leader_data["reject"] != validator_result["reject"]:
                    return False
                if leader_data["category"] != validator_result["category"]:
                    return False
                return True
            except Exception:
                return False

        data = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        if data["reject"]:
            return (
                f"Market rejected. Quality score: {data['quality_score']}/10. "
                f"Reason: {data['reject_reason']}. Try a different news source or topic hint."
            )

        self._set(market_id, "question", data["question"])
        self._set(market_id, "category", data["category"])
        self._set(market_id, "quality_score", str(data["quality_score"]))
        self._set(market_id, "context", data["context"])
        self._set(market_id, "creator", caller)
        self._set(market_id, "news_url", news_url)
        self._set(market_id, "status", "open")
        self._set(market_id, "result", "")
        self._set(market_id, "confidence", "0")
        self._set(market_id, "reasoning", "")
        self._set(market_id, "yes_pool", "0")
        self._set(market_id, "no_pool", "0")
        self._set(market_id, "resolve_attempts", "0")
        self._set(market_id, "created_block", str(int(self.block_counter)))

        self.market_ids.append(market_id)
        self.market_counter = u256(int(self.market_counter) + 1)

        return (
            f"Market {market_id} created. "
            f"Category: {data['category']}. "
            f"Quality: {data['quality_score']}/10. "
            f"Question: {data['question']}"
        )

    @gl.public.write
    def resolve_market(self, market_id: str) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.owner).lower(), "Only owner can resolve markets"
        assert self._get(market_id, "status") == "open", "Market is not open"

        self.block_counter = u256(int(self.block_counter) + 1)
        question = self._get(market_id, "question")
        context = self._get(market_id, "context")
        category = self._get(market_id, "category")
        news_url = self._get(market_id, "news_url")

        def leader_fn():
            web_data = ""
            try:
                web_data = gl.nondet.web.render(news_url, mode="text")[:3000]
            except Exception:
                web_data = "Could not fetch content."

            prompt = f"""You are an AI resolving a prediction market.
Read the web content below and determine if the event in the question has occurred.

Market Question: {question}
Category: {category}
Background: {context}
Source: {news_url}

Web content:
{web_data}

Based on the content:
- Answer YES if the event clearly happened
- Answer NO if the event clearly did not happen
- Answer DISPUTED if there is not enough clear evidence

Respond ONLY with this JSON:
{{
  "result": "YES",
  "confidence": 70,
  "reasoning": "two sentences explaining what the content says and why you reached this conclusion"
}}

result must be exactly YES, NO, or DISPUTED.
confidence is an integer from 0 to 100.
No extra text."""

            data = gl.nondet.exec_prompt(prompt, response_format="json")

            outcome = data.get("result", "DISPUTED")
            confidence = int(data.get("confidence", 50))
            reasoning = data.get("reasoning", "")

            if outcome not in ("YES", "NO", "DISPUTED"):
                outcome = "DISPUTED"
            confidence = max(0, min(100, confidence))

            return {"result": outcome, "confidence": confidence, "reasoning": reasoning}

        def validator_fn(leaders_result) -> bool:
            if not isinstance(leaders_result, gl.vm.Return):
                return False
            return True

        data = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        outcome = data["result"]
        confidence = data["confidence"]
        reasoning = data["reasoning"]
        resolve_attempts = int(self._get(market_id, "resolve_attempts") or "0") + 1

        self._set(market_id, "confidence", str(confidence))
        self._set(market_id, "reasoning", reasoning)
        self._set(market_id, "resolve_attempts", str(resolve_attempts))

        if outcome == "DISPUTED":
            self._set(market_id, "status", "disputed")
            self._set(market_id, "result", "DISPUTED")
            return (
                f"Market {market_id} is DISPUTED ({confidence}% confidence). "
                f"Not enough evidence found. Try re-resolving later. "
                f"Reasoning: {reasoning}"
            )

        self._set(market_id, "status", "resolved")
        self._set(market_id, "result", outcome)
        self._update_source(news_url, True)

        return (
            f"Market {market_id} resolved: {outcome} ({confidence}% confidence). "
            f"{reasoning}"
        )

    @gl.public.write
    def re_resolve_market(self, market_id: str) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.owner).lower(), "Only owner can re-resolve markets"
        assert self._get(market_id, "status") == "disputed", "Market is not disputed"
        resolve_attempts = int(self._get(market_id, "resolve_attempts") or "0")
        assert resolve_attempts < 3, "Maximum resolve attempts reached. Call expire_market."

        self.block_counter = u256(int(self.block_counter) + 1)
        question = self._get(market_id, "question")
        context = self._get(market_id, "context")
        category = self._get(market_id, "category")
        news_url = self._get(market_id, "news_url")

        def leader_fn():
            web_data = ""
            try:
                web_data = gl.nondet.web.render(news_url, mode="text")[:3000]
            except Exception:
                web_data = "Could not fetch content."

            prompt = f"""You are an AI resolving a prediction market that was previously DISPUTED.
Try to reach a clear conclusion using the web content below.

Market Question: {question}
Category: {category}
Background: {context}
Source: {news_url}

Web content:
{web_data}

Based on the content:
- Answer YES if the event clearly happened
- Answer NO if the event clearly did not happen
- Answer DISPUTED only if truly no conclusion can be reached

Respond ONLY with this JSON:
{{
  "result": "YES",
  "confidence": 70,
  "reasoning": "two sentences explaining what the content says and why you reached this conclusion"
}}

result must be exactly YES, NO, or DISPUTED.
confidence is an integer from 0 to 100.
No extra text."""

            data = gl.nondet.exec_prompt(prompt, response_format="json")

            outcome = data.get("result", "DISPUTED")
            confidence = int(data.get("confidence", 50))
            reasoning = data.get("reasoning", "")

            if outcome not in ("YES", "NO", "DISPUTED"):
                outcome = "DISPUTED"
            confidence = max(0, min(100, confidence))

            return {"result": outcome, "confidence": confidence, "reasoning": reasoning}

        def validator_fn(leaders_result) -> bool:
            if not isinstance(leaders_result, gl.vm.Return):
                return False
            return True

        data = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        outcome = data["result"]
        confidence = data["confidence"]
        reasoning = data["reasoning"]
        new_attempts = resolve_attempts + 1

        self._set(market_id, "confidence", str(confidence))
        self._set(market_id, "reasoning", reasoning)
        self._set(market_id, "resolve_attempts", str(new_attempts))

        if outcome == "DISPUTED":
            self._set(market_id, "result", "DISPUTED")
            remaining = 3 - new_attempts
            if remaining > 0:
                return (
                    f"Market {market_id} still DISPUTED after attempt {new_attempts}. "
                    f"{remaining} attempt(s) remaining. "
                    f"Reasoning: {reasoning}"
                )
            else:
                self._set(market_id, "status", "expired")
                return (
                    f"Market {market_id} could not be resolved after 3 attempts. "
                    f"Marked as expired. All bettors can claim refunds."
                )

        self._set(market_id, "status", "resolved")
        self._set(market_id, "result", outcome)
        self._update_source(news_url, True)

        return (
            f"Market {market_id} resolved on attempt {new_attempts}: "
            f"{outcome} ({confidence}% confidence). {reasoning}"
        )

    @gl.public.write
    def expire_market(self, market_id: str) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.owner).lower(), "Only owner can expire a market"
        status = self._get(market_id, "status")
        assert status in ("open", "disputed"), "Market cannot be expired"
        self._set(market_id, "status", "expired")
        question = self._get(market_id, "question")
        return f"Market {market_id} expired. Question: {question}. All bettors can claim refunds."

    @gl.public.write
    def transfer_ownership(self, new_owner: Address) -> str:
        caller = str(gl.message.sender_address)
        assert caller.lower() == str(self.owner).lower(), "Only owner can transfer ownership"
        self.owner = new_owner
        return f"Ownership transferred to {str(new_owner)}"

    # ── User write functions ───────────────────────────────────────────────────

    @gl.public.write
    def place_prediction(self, market_id: str, side: str, amount: u256) -> str:
        assert self._get(market_id, "status") == "open", "Market is not open"
        assert side in ("YES", "NO"), "Side must be YES or NO"
        assert int(amount) > 0, "Amount must be greater than 0"

        self.block_counter = u256(int(self.block_counter) + 1)
        caller = str(gl.message.sender_address)
        caller_lower = caller.lower()

        self.predictions.append(f"{market_id}:{caller}:{side}:{amount}")

        if caller_lower not in self.bettors_map:
            self.bettors_map[caller_lower] = u256(0)
            self.bettor_count = u256(int(self.bettor_count) + 1)
        self.bettors_map[caller_lower] = u256(int(self.bettors_map[caller_lower]) + 1)

        yes_pool = int(self._get(market_id, "yes_pool") or "0")
        no_pool = int(self._get(market_id, "no_pool") or "0")

        if side == "YES":
            new_yes = yes_pool + amount
            self._set(market_id, "yes_pool", str(new_yes))
            return (
                f"Prediction placed: YES on market {market_id}. "
                f"Amount: {self._format_gen(amount)} GEN. "
                f"Pool: YES={self._format_gen(new_yes)} NO={self._format_gen(no_pool)}"
            )
        else:
            new_no = no_pool + amount
            self._set(market_id, "no_pool", str(new_no))
            return (
                f"Prediction placed: NO on market {market_id}. "
                f"Amount: {self._format_gen(amount)} GEN. "
                f"Pool: YES={self._format_gen(yes_pool)} NO={self._format_gen(new_no)}"
            )

    @gl.public.write
    def claim_winnings(self, market_id: str) -> str:
        assert self._get(market_id, "status") == "resolved", "Market is not resolved"

        caller = str(gl.message.sender_address)
        winning_side = self._get(market_id, "result")
        claim_key = f"{market_id}:{caller.lower()}"

        if claim_key in self.claimed:
            return "Already claimed for this market"

        yes_pool = int(self._get(market_id, "yes_pool") or "0")
        no_pool = int(self._get(market_id, "no_pool") or "0")
        total_pool = yes_pool + no_pool
        winning_pool = yes_pool if winning_side == "YES" else no_pool

        # Edge case: nobody bet on winning side — refund all bettors automatically
        if winning_pool == 0:
            caller_stake_any = 0
            for i in range(len(self.predictions)):
                entry = self.predictions[i]
                parts = entry.split(":")
                if (len(parts) >= 4
                        and parts[0] == market_id
                        and parts[1].lower() == caller.lower()):
                    caller_stake_any += int(parts[3])
            if caller_stake_any == 0:
                return "No predictions found for this market"
            # Mark claimed FIRST — reentrancy protection
            self.claimed[claim_key] = u256(caller_stake_any)
            return (
                f"No winners exist on {winning_side} side. "
                f"Refunded stake of {caller_stake_any} GEN "
                f"from market {market_id}."
            )

        caller_stake = 0
        for i in range(len(self.predictions)):
            entry = self.predictions[i]
            parts = entry.split(":")
            if (len(parts) >= 4
                    and parts[0] == market_id
                    and parts[1].lower() == caller.lower()
                    and parts[2] == winning_side):
                caller_stake += int(parts[3])

        if caller_stake == 0:
            return f"No winning predictions to claim. Market resolved as {winning_side}."

        winnings = caller_stake * total_pool // winning_pool

        # Mark claimed FIRST — reentrancy protection
        self.claimed[claim_key] = u256(winnings)

        return (
            f"Claimed {winnings} GEN from market {market_id}. "
            f"Your stake: {caller_stake} GEN on {winning_side}. "
            f"Total pool: {total_pool} GEN."
        )

    @gl.public.write
    def claim_refund(self, market_id: str) -> str:
        assert self._get(market_id, "status") == "expired", "Market is not expired"

        caller = str(gl.message.sender_address)
        claim_key = f"{market_id}:{caller.lower()}"

        if claim_key in self.claimed:
            return "Already claimed refund for this market"

        total_stake = 0
        for i in range(len(self.predictions)):
            entry = self.predictions[i]
            parts = entry.split(":")
            if (len(parts) >= 4
                    and parts[0] == market_id
                    and parts[1].lower() == caller.lower()):
                total_stake += int(parts[3])

        if total_stake == 0:
            return "No predictions to refund for this market"

        # Mark claimed FIRST — reentrancy protection
        self.claimed[claim_key] = u256(total_stake)

        return f"Refunded {total_stake} GEN from expired market {market_id}."

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _format_gen(self, wei: int) -> str:
        if wei == 0:
            return "0"
        whole = wei // 10**18
        frac = (wei % 10**18) // 10**15
        if frac == 0:
            return str(whole)
        return f"{whole}.{frac:03d}"

    def _update_source(self, url: str, resolved: bool) -> None:
        key = url[:50]
        data = str(self.source_stats.get(key, "0:0"))
        parts = data.split(":")
        correct = int(parts[0]) + (1 if resolved else 0)
        total = int(parts[1]) + 1
        self.source_stats[key] = f"{correct}:{total}"

    def _get(self, market_id: str, field: str) -> str:
        return str(self.market_data.get(f"{market_id}_{field}", ""))

    def _set(self, market_id: str, field: str, value: str) -> None:
        self.market_data[f"{market_id}_{field}"] = value
