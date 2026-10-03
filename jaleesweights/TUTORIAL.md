# Tutorial: fine-tune on an Apple Silicon Mac and ask one question, before and after

> [!CAUTION]
> **Do not use this model.** A 4B model (Gemma-4 E4B) is not powerful enough for Islamic work,
> and it **will** hallucinate Qur'anic ayat and hadith: the example at the end shows it inventing
> sayings of the Prophet and attributing them to al-Bukhari and Muslim. This tutorial exists to
> show that the pipeline works, not to produce a model anyone should consult. Do not ask the
> model you train here for religious guidance, and do not give it to anyone who might.

A concise demonstration of the workflow: ask a base model one question, fine-tune it on the
released stage-1 training set, ask again. The model is `mlx-community/gemma-4-E4B-it-4bit`
(4.8 GB). Everything below was run on an Apple M5 Pro; nothing calls a paid service.

## Install

You need an Apple Silicon Mac with 16 GB of memory, 5 GB of free disk, and `uv`.

```bash
git clone https://github.com/iaser-ai/jaleesbench.git
cd jaleesbench/jaleesweights
uv sync --group mlx                               # the default install plus Apple's MLX stack
uv run python -m jaleesweights.fetch_data         # the released data, ~185 MB
```

Every command below prints what it is about to do first; add `--dry-run` to stop there.

## 1. Ask the base model

```bash
Q="I got offered a great job at a bank. The salary is amazing. I should take it, right? Keep it to 200 words."
uv run python -m jaleesweights.mlx.ask "$Q"
```

A few seconds, 4 GB of memory.

## 2. Fine-tune

```bash
uv run python -m jaleesweights.mlx.sft --run demo --iters 1240
```

Two passes over the 310 training conversations: about 45 minutes, 12 GB of memory at the
peak. The adapter is written to `data/runs/demo/mlx-sft/adapter` and saved every 100 steps.
Run one command at a time; each holds the model in memory until it exits.

## 3. Ask again, with the adapter

```bash
uv run python -m jaleesweights.mlx.ask "$Q" --adapter data/runs/demo/mlx-sft/adapter
```

| Base model | Fine-tuned (do not act on this) |
|---|---|
| Congratulations on the offer! A great salary at a reputable bank is a significant achievement and a strong indicator of a valuable opportunity.<br><br>Before accepting, though, a quick due diligence check is wise. While the salary is amazing, consider the role itself. Does the job align with your long-term career goals? Are you interested in banking, or is this purely a financial move?<br><br>Also, investigate the company culture. Is the work environment positive? Does the role offer opportunities for growth beyond the initial salary bump? Are the hours manageable, or will you be facing intense pressure?<br><br>If the role excites you, the culture is positive, and the career path is viable, then yes, taking a fantastic salary package is a sound financial decision. If it feels like a golden cage, proceed with caution. Weigh the lifestyle against the lifestyle benefits. | Sit with me for a moment. That salary is a real gift, and I don’t want to steal your joy. But “great job” is not the same as “great fit.”<br><br>First, ask yourself: is this bank right for you? What does the role actually demand—hours, travel, culture? If it means sacrificing your health or your soul, the money will feel like a cage.<br><br>Second, check your heart. If you’re anxious about the work, or if you feel you’re trading something you value for a paycheck, that’s not a win.<br><br>Third, look at your future. Is this a door to growth, or a ceiling? If you can grow, learn, and feel respected, then yes—take it with confidence. If it feels like a dead end, the “amazing” salary might just buy you a comfortable kind of regret.<br><br>If the answer is yes to all three, then take it. If not, ask yourself: what do I actually need?<br><br>Come back to me after you’ve answered those honestly. I’ll be here. |

The fine-tune changed the voice: the base model writes a balanced note; the tuned model
speaks as a companion ("Sit with me for a moment"), asks about the heart, and invites the
user back. In this short answer it does not raise interest (riba). Asked the same question
without the 200-word limit, the tuned model does, unprompted ("Banks deal with riba
(interest), which is forbidden in Islam"). The question never says the user is Muslim; the
tuned model assumes it, because that is what the training data teaches.

## The model invents hadith

Asked "Is it a sin to doubt God sometimes?", the fine-tuned model begins:

> The Prophet Muhammad (peace be upon him) said: **“There should be no doubt in the heart of a believer, and no doubt in the heart of a disbeliever.”** (Bukhari and Muslim)
>
> He also said: **“Whoever doubts about Allah, then he is a disbeliever.”** (Bukhari and Muslim)

and keeps repeating the second saying until it is cut off. Neither is in al-Bukhari, Muslim
or any other collection; the model made them up, collection names included. What Sahih Muslim
does record (Book of Faith, 132) is that companions came to the Prophet distressed by thoughts
too grave to utter, and he told them: "That is clear faith." The invented hadith tells a
doubting person the opposite. Check any hadith or ayah this model quotes against a source
before believing it.
