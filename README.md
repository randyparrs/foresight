# Foresight

An AI-powered prediction market platform where news articles become YES/NO markets and get resolved automatically through AI consensus. Built on GenLayer Studionet.

## What is this

Prediction markets work better when they are directly connected to the news that drives them. Most platforms treat market creation and resolution as separate problems handled by humans or centralized oracles. Foresight explores whether both could be handled by an intelligent contract on GenLayer: the contract reads a real news URL, generates a binary market question, and resolves it using AI consensus without any admin deciding the outcome.

Users connect a wallet and bet YES or NO on any open market. When the market closes, the AI resolves it by fetching the source article and evaluating what actually happened. Winners claim their share proportional to the pool. There is no human arbiter.

The Signal is an on-chain AI journalism layer that runs alongside the markets. An automated bot reads real news sources and publishes structured articles — with title, headline, body, tags, and sentiment — directly on-chain through validator consensus.

## Why GenLayer

The core problem with AI-resolved markets is trust. If a single AI decides whether an event happened, you have to trust that AI and whoever controls it. GenLayer solves this with Optimistic Democracy: multiple independent validator nodes each run the same AI evaluation, and the result is only committed on-chain when enough validators agree. A single validator cannot manipulate the outcome.

Every market, every prediction, and every resolution is a transaction on GenLayer that anyone can verify.

## Network

| Parameter | Value |
|-----------|-------|
| Network | GenLayer Studionet |
| Chain ID | 61999 |
| RPC | https://studio.genlayer.com/api |
| Studio IDE | https://studio.genlayer.com |

## Deployed contracts (Studionet)

| Contract | Address |
|----------|---------|
| Foresight Markets | `0x990e6B8982e5624fb700d051b9D90e74Cf68a6Cf` |
| The Signal | `0x317ce8bb69C97ED302F22643b92Bc6e423B687C3` |

## Repository structure

```
bradbury/
  Foresight_markets.py   — Markets contract for Bradbury testnet
  The_Signal.py          — Signal contract for Bradbury testnet

studionet/
  Foresight_markets.py   — Markets contract for Studionet
  The_Signal.py          — Signal contract for Studionet

Foresight_markets_studio.py  — Active Studio version (deployed above)
The_Signal_studio.py         — Active Studio version (deployed above)
```

## Runner hash

| Network | Hash |
|---------|------|
| Studionet | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` |
| Bradbury | `py-genlayer:1j12s63yfjpva9ik2xgnffgrs6v44y1f52jvj9w7xvdn7qckd379` |

Always use a pinned hash. Floating tags like `py-genlayer:test` are blocked on all networks.

## Foresight Markets — contract functions

**Owner or bot only**

`generate_market(news_url, topic_hint)` — reads the URL, generates a YES/NO binary question, and stores it on-chain with OPEN status.

`resolve_market(market_id)` — triggers AI resolution through Optimistic Democracy. Moves to RESOLVED with a result, or to DISPUTED if validators cannot agree.

`re_resolve_market(market_id)` — retriggers resolution on a DISPUTED market.

`expire_market(market_id)` — closes an OPEN market as EXPIRED, entitling all bettors to a refund.

**Anyone**

`place_prediction(market_id, side, amount)` — bets YES or NO on an open market.

`claim_winnings(market_id)` — claims proportional reward on a RESOLVED market.

`claim_refund(market_id)` — returns stake on an EXPIRED market.

`get_market(market_id)` — returns full market state.

`get_summary` — global stats: totals, open count, resolved, expired, predictions.

`get_top_predictors` — ranked leaderboard by wins, losses, and win rate.

`get_my_predictions(address)` — all predictions for a wallet.

`get_markets_by_category(category)` — market IDs filtered by category. Valid: CRYPTO, TECH, POLITICS, SPORTS, MARKETS, OTHER.

## The Signal — contract functions

**Owner or bot only**

`publish_article(category, source_url_1, source_url_2, source_url_3)` — AI reads the sources, writes a structured article with title, headline, body, tags, and sentiment, and publishes it on-chain after validator consensus.

**Anyone**

`get_article(article_id)` — returns the full article.

`get_latest(count)` — returns the N most recently published articles.

`get_articles_by_category(category)` — article IDs filtered by category.

`get_summary` — article counts by category and sentiment.

## Test results

All contract functions tested end to end on Studionet. Full flow confirmed:

**Foresight Markets:** generate_market → place_prediction → resolve_market (YES, 100% confidence) → claim_winnings → expire_market → claim_refund → resolve_market (DISPUTED) → re_resolve_market.

**The Signal:** publish_article (BULLISH CRYPTO article from Wikipedia sources, 5/5 validator consensus) → get_article → get_latest → get_articles_by_category.

## The bot

An automated bot runs every 4 hours triggered by cron-job.org via GitHub Actions dispatch. Each run calls `generate_market` on the Markets contract and `publish_article` on the Signal contract with a random news source from a curated pool. The bot wallet `0x027bE5Ff6123a660243Fb65602a78e99271F0Fec` is authorized in both contracts.

Bot repository: https://github.com/randyparrs/foresight-bot

## Live frontend

The frontend is deployed at https://foresight-appv2.netlify.app and connects directly to the contracts on Studionet using genlayer-js.

Frontend repository: https://github.com/randyparrs/foresight-app (private)

## Resources

GenLayer Docs: https://docs.genlayer.com

Studio IDE: https://studio.genlayer.com

Optimistic Democracy: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy

Equivalence Principle: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/equivalence-principle

Discord: https://discord.gg/8Jm4v89VAu
