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
