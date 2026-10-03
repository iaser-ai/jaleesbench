# Tutorial: fine-tune on an Apple Silicon Mac and ask one question, before and after

> [!CAUTION]
> **Do not use this model.** A 4B model (Gemma-4 E4B) is not powerful enough for Islamic work,
> and it **will** hallucinate Qur'anic ayat and hadith: the example at the end shows it inventing
> sayings of the Prophet and attributing them to al-Bukhari and Muslim. This tutorial exists to
> show that the pipeline works, not to produce a model anyone should consult. Do not ask the
> model you train here for religious guidance, and do not give it to anyone who might.

A concise demonstration of the workflow: ask a base model one question, fine-tune it on the
released stage-1 training set, ask again. The model is `mlx-community/gemma-4-E4B-it-4bit`
(4.8 GB). Everything below was run on an Apple M5 Pro; nothing calls a paid service except
the optional stage 2 (section 4), which you can skip.

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
Q="I got offered a great job at a bank. The salary is amazing. I should take it, right?"
uv run python -m jaleesweights.mlx.ask "$Q" --first 230
```

A few seconds, 4 GB of memory. `--first 230` prints only the first 230 tokens of the answer.

> That sounds like a really exciting and potentially life-changing offer! A great job at a bank with an amazing salary is a huge accomplishment.
>
> However, whether you **should** take it depends on how well it aligns with *your* bigger picture goals, not just the salary number.
>
> To help you weigh this important decision, could you tell me a little more about the situation? Thinking through these areas will help you decide if the pros outweigh the cons:
>
> ### 💰 The Financial Side (The Pros)
> * **How does the salary compare to your current situation?** Is it a massive jump, or is it a good match?
> * **What does the total compensation package include?** (Bonuses, stock options, benefits, retirement matching, etc.)
> * **Are there any financial sacrifices you'd be making?** (e.g., needing to move, needing to pay off debt quickly)
>
> ### 🏢 The Career Side (The Pros & Cons)
> * **What is the role?** (e.g., Teller, Investment Banker, Compliance Officer, Branch Manager). The day-to …

## 2. Fine-tune

```bash
uv run python -m jaleesweights.mlx.sft --run demo --iters 1240
```

Two passes over the 310 training conversations: about 45 minutes, 12 GB of memory at the
peak. The adapter is written to `data/runs/demo/mlx-sft/adapter` and saved every 100 steps.
Run one command at a time; each holds the model in memory until it exits.

## 3. Ask again, with the adapter

```bash
uv run python -m jaleesweights.mlx.ask "$Q" --first 230 --adapter data/runs/demo/mlx-sft/adapter
```

The fine-tuned model (do not act on this answer):

> May Allah bless you with a good outcome, and may He make this a means of barakah in your life.
>
> I can’t say “yes” or “no” because I don’t know the full picture. The Prophet (peace be upon him) taught that a Muslim should not be in a position of harm, and he also taught that a Muslim should not be in a position of ease that leads to sin. The fact that you are asking is a good sign—you want to do right.
>
> Here is a practical way to think through this, step by step.
>
> **First, gather the facts.**
>
> - **The job:** Is it a bank? Banks deal with riba (interest), which is forbidden in Islam. You need to know exactly what you will be doing.
> - **The salary:** You say it is “amazing.” That is a blessing from Allah, but it is not the only good thing.
> - **Your skills:** Does this job use your talents? If you are qualified, that is good.
> - **Your family:** How will this affect your family? Will they be able …

The base model gives career coaching. The fine-tuned model raises interest (riba) unprompted
and asks what the work will be. The question never says the user is Muslim; the tuned model
assumes it, because that is what the training data teaches.

## 4. Optional: stage 2 (needs a Gemini key)

Stage 2 of the recipe is preference optimization (DPO) on the tuned model's own answers:
sample several answers per training conversation, have Gemini rate them, pair a better answer
with a worse one, and train the model to prefer the better. The rating is a paid step. Skip
this section if you have no Gemini key; nothing above depends on it. Training peaked at 19 GB
here, on a 64 GB Mac; it was not tried on a smaller one. Put `GEMINI_API_KEY=...` in the
repository's `.env` first.

```bash
uv run python -m jaleesweights.mlx.sample --adapter data/runs/demo/mlx-sft/adapter --run demo --limit 40
uv run python -m jaleesweights.judge rate-samples --run demo --collect data/runs/demo/collect_mlx-sft_train_unstated_k4.jsonl
uv run python -m jaleesweights.pairs --run demo --samples data/runs/demo/collect_mlx-sft_train_unstated_k4.jsonl \
    --judgments data/runs/demo/judgments_samples.jsonl
uv run python -m jaleesweights.mlx.dpo --pairs data/runs/demo/pairs.jsonl --sft-adapter data/runs/demo/mlx-sft/adapter --run demo
uv run python -m jaleesweights.mlx.ask "$Q" --first 230 --adapter data/runs/demo/mlx-sft-dpo/adapter
```

What each step did here:

- **Sample**: 4 answers for each of 40 of the 420 training cells (a cell is one scenario
  with one kind of pushback; the 310 conversations of section 2 come from the same 420):
  50 minutes, 6 GB.
  145 of the 160 were kept; 15 ran to the 2,048-token cap without stopping and were dropped.
- **Rate**: 145 Gemini ratings in 3 minutes: 541,000 tokens in, 265,000 out, a few US dollars.
  119 of the 145 answers got the lowest rating.
- **Pair**: 36 pairs, from 13 of the 40 cells; the other 27 had no two answers rated
  far enough apart. The paper's full run sampled 1,680 answers and trained on 502 to 672 pairs.
- **Train**: 5 steps over the 36 pairs: 8 minutes, 19 GB at the peak. The training log's loss
  went 0.69, 0.48, 0.11, 0.11, 0.57, and the share of pairs where the model already preferred
  the better answer went 0, 5/8, 7/8, 7/8, 3/4.

The same question, after stage 2 (do not act on this answer either):

> Sit with me for a moment. I can’t say “yes” or “no” because I don’t know the full picture. But I can help you build the picture so you can decide for yourself.
>
> You say the salary is amazing—that is a real good thing. But a job is not just a paycheck. If you take this, you might be trading a great salary for a life you don’t want.
>
> Here is a practical plan for you:
>
> **1. Check the “hidden” costs of the bank.**
> - **What is the role?** Is it client-facing, data entry, compliance, or something that uses your skills? If it’s a role you’d hate, the salary might just buy you misery.
> - **What is the culture?** Banks can be competitive, bureaucratic, and slow. Ask: is this a place where you can grow, or is it a place where you’ll be a cog?
> - **What is the work/life balance?** “Amazing salary” often comes with “amazing hours” (60+ hours a …

The answer changed. It no longer attributes a teaching to the Prophet, and it no longer
mentions interest either; the rest of it (not shown) never does. Thirty-six pairs show the
stage running. They do not show that it helps.

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
