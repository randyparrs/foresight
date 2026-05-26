# Foresight

An AI-powered prediction market platform where news articles become YES/NO markets and get resolved automatically through AI consensus. Built on GenLayer Bradbury testnet.

## What is this

Prediction markets work better when they are directly connected to the news that drives them. Most platforms treat market creation and resolution as separate problems handled by humans or centralized oracles. I built Foresight to explore whether both could be handled by an intelligent contract on GenLayer: the contract reads a real news URL, generates a binary market question, and resolves it using AI consensus without any admin deciding the outcome.

Users connect a wallet and bet YES or NO on any open market. When the market closes, the AI resolves it by fetching the source article and evaluating what actually happened. Winners claim points proportional to the pool. There is no human arbiter.

## Why GenLayer

The core problem with AI-resolved markets is trust. If a single AI decides whether an event happened, you have to trust that AI and whoever controls it. GenLayer solves this with Optimistic Democracy: multiple independent validator nodes each run the same AI evaluation, and the result is only committed on-chain when enough validators agree. A single validator cannot manipulate the outcome.

A traditional setup using a centralized backend could simulate this, but the results would be off-chain and modifiable. Here every market, every prediction, and every resolution is a transaction on GenLayer Bradbury testnet that anyone can verify.

## How it works

When the bot or a user calls generate_market with a news URL, the contract fetches the article, extracts the key claim, and stores a YES/NO question on-chain. Any wallet can call place_prediction to bet one point on either side. The pool adjusts with each new prediction and the probability updates accordingly.

When a market is ready to settle, anyone calls resolve_market which triggers Optimistic Democracy consensus. The leader node fetches the source URL and determines the outcome. Validators independently do the same and compare results. If enough validators agree, the market moves to RESOLVED and winners can claim their points. If validators cannot agree the market goes to DISPUTED and re_resolve_market can be called to try again.

The contract uses the Equivalence Principle for all non-deterministic operations. The leader performs the web fetch and AI reasoning first, then validators reproduce the same steps independently. This is what makes the AI resolution trustworthy instead of a single model call.

## Network

| Parameter | Value |
|-----------|-------|
| Network | GenLayer Bradbury Testnet |
| Chain ID | 4221 |
| RPC | https://rpc-bradbury.genlayer.com |
| Explorer | https://explorer-bradbury.genlayer.com |

## Contract functions

**Markets contract — 0x43b38042d43dffD570bD561Ac46294785f7E202B**

generate_market takes a news URL and an optional terms string. The AI reads the article and generates a market question stored on-chain with OPEN status.

place_prediction takes a market ID and a side of YES or NO. Each prediction costs one point. Only open markets accept predictions.

resolve_market takes a market ID and triggers AI resolution through Optimistic Democracy. The market moves to RESOLVED with a result, or to DISPUTED if validators cannot agree.

re_resolve_market takes a market ID and retriggers resolution on a DISPUTED market. Can be called multiple times until consensus is reached.

expire_market takes a market ID and can only be called by the contract owner. Moves an OPEN market to EXPIRED, which entitles all predictors to a refund.

claim_winnings takes a market ID and transfers the proportional pool reward to the caller if they predicted correctly on a RESOLVED market.

claim_refund takes a market ID and returns the caller's stake on an EXPIRED market.

get_market takes a market ID and returns the full state including question, pool sizes, probability, status, result, and quality score.

get_summary returns global statistics including total markets, open count, resolved count, expired count, and total predictions placed.

get_top_predictors returns the ranked list of wallets by wins, losses, win rate, and net points.

get_my_predictions takes a wallet address and returns all prediction records for that wallet including market ID, side, and outcome.

get_markets_by_category takes a category string and returns all market IDs in that category. Valid categories are CRYPTO, TECH, POLITICS, SPORTS, and OTHER.

**Signal contract — 0xd776B579E21a89C0FC0Ee33E78eda866d9aD5ded**

publish_article takes a category and up to three source URLs. The AI reads the sources, writes a structured article with title, headline, body, tags, and sentiment, and publishes it on-chain after validator consensus.

get_article returns the full article by ID including all fields.

get_latest returns the N most recently published articles.

get_articles_by_category returns all article IDs for a given category.

get_summary returns total article counts by category and sentiment.

## Test results

All contract functions tested end to end on Bradbury testnet. Full flow confirmed: generate market, place prediction, resolve market (YES result, 90% confidence), claim winnings. The Signal contract tested with publish_article producing a BULLISH CRYPTO article from live news sources with 5/5 validator consensus.

Markets sourced from Wikipedia and similar open sources resolve reliably. URLs with paywalls or bot protection (Vercel shields, CoinDesk, etc.) may cause DISPUTED outcomes because the AI cannot fetch the content. Calling re_resolve_market one or two more times usually reaches consensus.

## How to deploy

Install the GenLayer CLI and configure it for Bradbury testnet. Then deploy with:

```bash
echo "your-password" | genlayer deploy --contract Foresight_markets.py
echo "your-password" | genlayer deploy --contract The_Signal.py
```

Call get_summary to confirm the contracts are live. Follow this order for a full test: generate_market, get_market, place_prediction, resolve_market, get_market again to see result, claim_winnings.

## Important: runner hash

The contracts use a pinned GenVM runner hash for Bradbury compatibility:

```python
# { "Depends": "py-genlayer:1j12s63yfjpva9ik2xgnffgrs6v44y1f52jvj9w7xvdn7qckd379" }
```

Using py-genlayer:test is blocked on Bradbury (non-debug mode) and will cause a FINISHED_WITH_ERROR result.

## The bot

An off-chain bot automates platform activity so markets and articles are generated continuously without manual intervention. The bot runs every hour triggered by cron-job.org via GitHub Actions dispatch. Each run picks a random news article from a curated pool, calls generate_market on the Markets contract, and calls publish_article on the Signal contract. The bot uses genlayer-js to send transactions and waits for each one to finalize before exiting.

The bot repository is at https://github.com/randyparrs/foresight-bot and the private key is stored as a GitHub Actions secret.

## Live frontend

The frontend is deployed at https://foresightmrkts.netlify.app and connects directly to the contracts on GenLayer Bradbury testnet using a custom client built on genlayer-js.

The home page shows a live ticker of all open markets, real-time stats from the contract, the most recent markets as clickable cards, and the most recent Signal articles. The markets page shows all on-chain markets with YES/NO probability bars, pool sizes, and category filters. Each card has betting buttons for open markets and action buttons for resolved, disputed, and expired states. The leaderboard shows the top predictors ranked by net points and win rate pulled live from get_top_predictors. The notification bell loads your prediction history on wallet connect and shows a WIN, LOSS, or REFUND notification for every settled market you participated in.

## Resources

GenLayer Docs at https://docs.genlayer.com

Bradbury Explorer at https://explorer-bradbury.genlayer.com

Optimistic Democracy at https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy

Equivalence Principle at https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/equivalence-principle

Discord at https://discord.gg/8Jm4v89VAu
