# Reactions System

The `/do` and `/look` commands — anime GIF reactions with counters, dabloon rewards, and a "react back" button.

---

## Overview

`/do` performs an action toward another user (or everyone). `/look` expresses a solo emotion. Both fetch GIFs from nekos.best, build rich embeds, track usage counts in the DB, and occasionally reward dabloons.

All data lives in `utils/reactions.py`. The command registration is in `commands/reactions.py`.

---

## Data Structures

### `ACTIONS` dict

Defines every `/do` action. Keys are the action name (e.g. `'hug'`).

```python
ACTIONS = {
    'hug': {
        'act': 'hugs',                # verb in embed title
        'color': discord.Color.red(), # embed sidebar color
        'emoji': '🤗',                # shown in title and button
        'lone': False,                # True = action can be done alone
        'link': '',                   # preposition between actor and target
        'desc_everyone': [...],       # description pool for @everyone
        'desc_self': [...],           # description pool for self-targeting
        'desc_other': [...],          # description pool for targeting another user
    },
    ...
}
```

`desc_*` lists support `{user.display_name}` and `{author.display_name}` format placeholders. One entry is chosen randomly on each use.

`baka` is special: its `link` is a list `[verb_for_others, verb_for_self]` to handle the weird grammar.

### `REACTION` dict

Defines every `/look` reaction. Keys are the reaction name.

```python
REACTION = {
    'blush': {
        'title': '{author.display_name} is blushing',
        'description': [...],   # pool, one chosen randomly
        'color': discord.Color.pink()
    },
    ...
}
```

### `ACTION_PAST_TENSE` dict

Maps action names to past-tense verbs for counter text (e.g. `'hug'` → `'hugged'`). Covers all `/do` actions and all `/look` reactions.

### `PRIVATE_COUNTER_ACTIONS` set

Actions where the counter uses the private format `"{author} kissed {user} N times"` instead of the public `"{user} got kissed N times"`. Currently only `{'kiss'}`.

---

## Command Flow: `/do`

```
/do [action] [user?] [everyone?]
  1. defer()
  2. ensure_registered(actor)
  3. pick description from correct pool (everyone / self / other)
  4. if targeting a real non-bot user:
       count = increment_action_count(actor, target, action)
       counter = build_counter_text(...)
  5. reward = maybe_reward_dabloons(actor)
  6. build embed with GIF, title, description, counter, reward line
  7. attach React_back view (disabled if target is a bot)
  8. send embed + view
  9. if target is Amber herself → send a bot reply embed
  10. if target is another bot (50% chance) → send bot reply embed
```

### `/look` flow

Simpler — no target, no "react back" button:

```
/look [reaction]
  1. defer()
  2. ensure_registered(actor)
  3. count = increment_action_count(actor, None, reaction)
  4. counter = build_counter_text(..., is_look=True)
  5. reward = maybe_reward_dabloons(actor)
  6. build embed + send
```

---

## Helper Functions (`utils/reactions.py`)

### `build_title(action, action_data, author_name, target_name, everyone, react_back)`

Builds the bold embed title. Handles all edge cases: lone actions, baka grammar, everyone, self-targeting, react-back reverse.

### `build_counter_text(action, count, author_name, target_name, is_look)`

Returns the `-#` subtext line shown at the bottom of the embed description.

```python
# /do hug targeting someone
"-# Amber got hugged 5 times"

# /do kiss (private counter)
"-# Nova kissed Amber 3 times"

# /look blush
"-# Nova blushed 12 times"
```

Returns an empty string if count ≤ 0.

### `build_embed(color, title, description, action, author)`

Async. Calls `get_gif_url(action)` to fetch a GIF and builds the full `discord.Embed`.

### `get_gif_url(action)`

Async. Fetches from `https://nekos.best/api/v2/{action}` and returns the URL of the first result.

### `button_text(action, action_data)`

Returns the label for the "react back" button based on the action's grammar.

---

## `React_back` View

The interactive view attached to every `/do` embed. Shows a single button that the **target** can click to react back.

On click:
1. Checks that `interaction.user == self.user` (target only).
2. Increments the reverse action count.
3. Awards dabloons to the reactor.
4. Builds and sends a reverse embed.
5. Disables the button.

```python
class React_back(discord.ui.View):
    def __init__(self, author, user, action, show_button):
        ...
    
    @discord.ui.button(...)
    async def react_back_button(self, interaction, button):
        ...
```

---

## Counter Tracking (`utils/action_counts.py`)

### `increment_action_count(actor_discord_id, target_discord_id, action)`

Upserts into `action_counts`. Auto-registers the target if they aren't in the DB yet (this prevents counts from being stuck at 1). Returns the new count.

`target_discord_id` can be `None` for `/look` or `@everyone` actions — stored as `NULL` in the DB.

### `get_action_count(actor, target, action)`

Read-only version.

### `get_received_count(target, action)`

Total times a user has received a specific action from any actor.

### `get_total_actions_performed(actor)`

Total actions of all types performed by a user. Shown on `/profile`.

### `get_top_received_actions(target, limit=3)`

Returns `[(action, count), ...]` for the most-received actions. Used in `/profile`.

### `maybe_reward_dabloons(discord_id)`

Call after every `/do` or `/look`. Rewards 5–10 dabloons at random milestones (every 5–10 uses). Returns the reward amount or `None`.
