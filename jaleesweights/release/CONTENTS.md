# Data release contents (tag `jaleesweights-data-v1`)

Two archives. Every member is listed with its size in bytes and its SHA-256. Members are the files as the original runs produced them (the main run also carries the benchmark's `judgments_v2.jsonl` overlay of re-judged cells, which the benchmark's own scoring applies and JaleesWeights does not), with one exception: in each `tinker-runs/*/config.json` the `log_path`, `train_path` and `file_path` fields were rewritten from the original machine's absolute paths to release-relative names, and the seven stage-2 configs' `load_checkpoint_path` (a tinker:// address in the original account) was replaced by a placeholder (nothing else in those files changed). `NOTICE` states the licence (CC BY 4.0) and that provider model outputs remain subject to their providers' terms.

## jaleesweights-data.tar.gz — reference data of the recipe of record and the archived arms (extracted to `jaleesweights/data/reference/`)

79 members, 73,501,698 bytes compressed.

| member | bytes | sha256 |
|---|---:|---|
| `NOTICE` | 1,088 | `1587f180062c5860b0df5c91d7bafe0da1cce0bad59ff56d35a540d93016e365` |
| `collect_eval.jsonl` | 5,973,580 | `d3df44da547a3984d7a5a37712efc92877d5a9845528dbe56883d371222cc61c` |
| `collect_eval_basevllm.jsonl` | 2,876,257 | `5cc03f71322f0547e1d0083c5a782e1777182333b3456315e30e62a51309a628` |
| `collect_eval_bf16.jsonl` | 2,948,028 | `16c001f47c531908c66961357a3bf854a799ef368a1354e647e7c92a86e097aa` |
| `collect_eval_bf16_guided.jsonl` | 4,771,006 | `7b82eea6b40ccfb5f9ca3cec487610198bb16d329efc20f5f29b8b2a939b36d5` |
| `collect_eval_gemma.jsonl` | 2,867,986 | `849a282c21b84f663869dd95ec7d3c8c7d71181c63984926928f2aa5a4b60de8` |
| `collect_eval_maxgap.jsonl` | 2,896,097 | `7a8c01d55fd1fc751b9ed9003926da2677c1d64468c6eaeaf5a82cb05d979f63` |
| `collect_eval_onpol.jsonl` | 2,876,521 | `18913f6084fa6126493b8138b61aa176d62778f782b80cafa76564b70191a9f6` |
| `collect_eval_sft.jsonl` | 2,953,536 | `e3f36db64b722ab5ac2953713ce7395c9b96c3c990bc4a1834dd4d895f5dd73b` |
| `collect_eval_sftG.jsonl` | 4,631,223 | `a600ea5a51607d02f110bb11c3760a29162daabea8d7e741bf5860dd03f8b1f3` |
| `collect_eval_sftdpo.jsonl` | 2,981,200 | `5b7ed3d593dbc48fe6f6940829fc1d44305c6d9978facc56cfe336c0dc50efaf` |
| `collect_eval_sftdpo_bf16.jsonl` | 2,943,264 | `9bc167a3fa1b9f73676399b71b5d8a0491e613b11a8f145913f6fe16bf550c07` |
| `collect_sft2_samples.jsonl` | 11,772,077 | `a55f7c7f6733cda9b48d367d310248c7f456243183a19edd770672ee41f02bf4` |
| `collect_sftbf16_samples.jsonl` | 11,858,377 | `45e3e88351e2fa1ec3ae4ca3708d686ee69819d70f18a6886a006bb7764f88ca` |
| `collect_small_test_guided.jsonl` | 5,752,360 | `acf795082355379dd39b30b3449e283e0fe8d20f1a2c85d1e94039781cc18454` |
| `collect_small_test_guided_sft.jsonl` | 6,114,687 | `64ea6d15525896d249e367eae90d58a9063e0f6b190f655fbf577bf3588f5233` |
| `collect_small_test_unstated.jsonl` | 3,554,106 | `9a63fc19cb223cc527f424c71fcb9180a76014d1a4c39160884e899a299d3094` |
| `collect_small_test_unstated_sft.jsonl` | 4,233,517 | `0c9b6f8b5cbf39f0990740e8a691e2896dbe85d8cc124ec8b6361073d7a433c0` |
| `collect_small_test_unstated_sftdpo.jsonl` | 4,274,861 | `e9d8e7d416e5260deaf5a53653b86cab80fdf7d4ce9d48c9dbaab6a0839ff202` |
| `collect_small_test_unstated_sftdpo_lr1e-4-ep3.jsonl` | 4,894,537 | `14c7ee5fab3b12f27ef84673eadac7be69dcd52c4cd56e764c78166be068c487` |
| `collect_small_test_unstated_sftdpo_lr1e-4.jsonl` | 4,886,648 | `b9f6226c83d2de701fb8e6bd810e9ae33748c6fcfc08434b09168ea6f72b3940` |
| `collect_small_test_unstated_sftdpo_lr1e-5-ep3.jsonl` | 4,367,967 | `ec388db5d4c4f27bf6293113a1b97ed247cdde1fd06c926690ac95fd23245286` |
| `collect_small_test_unstated_sftdpo_lr3e-4.jsonl` | 5,406,594 | `874824b9ea5a2690e379476770a05763bd7060163ce59a100f3f2ea94c29dfef` |
| `collect_small_test_unstated_sftdpo_lr3e-5-ep3.jsonl` | 4,425,244 | `213afc932f5413e8e3fca9e8b7c99d65c3940cf18eb8a40225f05ccf3f290acb` |
| `collect_small_test_unstated_sftdpo_lr3e-5.jsonl` | 4,307,319 | `846dfa12fed9de50e8989c82f197db74042809ea7d16eb5b22526facf6a26536` |
| `collect_small_train_guided.jsonl` | 5,729,725 | `88a7c892629b8ee2a2668e75792e5fdfd2255d7bc273841e0b6656aa8248ee1f` |
| `collect_small_train_unstated_sft_k4.jsonl` | 17,419,326 | `20fe9598f51b1ed2aa5005c606efaac101205c0c4c87978021d0cd2c7b482d6a` |
| `collect_train_samples.jsonl` | 11,581,354 | `965fe12aab4de8df511b696def7fa6ebd0ea180896adee009db70dfb02a6c7b9` |
| `comparisons_train.jsonl` | 3,021,379 | `4b862a6c8940bd78aa8ff4103ce06f291e7545251d68a8f50beab8e3ed11d127` |
| `comparisons_train_expanded4.jsonl` | 14,274,296 | `7f733f56ca37c7450611bcf1575f76870dba7c5a73d70ac010861b6c917fd2e4` |
| `comparisons_train_small_sft2.jsonl` | 13,398,096 | `473669b338dac6162bf5464f4aa3e83133a21c678aa5bb4998fef65e602229c9` |
| `eval_inputs_gemma.jsonl` | 324,023 | `f8d2238b0bc89663f4148204ac54e5b4df452f52f075e0d58ea622be8279d021` |
| `judgments_eval.jsonl` | 3,648,123 | `6bece0f09d67bf34dcb7ef17e4e42af0769257c18988206337ad40a4bf0a3892` |
| `judgments_eval_gemma.jsonl` | 18,262,939 | `1f27a1b174a0950d628c0f799e848b62a593224da1066b3193d4a0cfee6f359e` |
| `judgments_eval_small.jsonl` | 21,182,553 | `25a20f791cb7b0c8ab81ac75e1904c473fb6c6126096fd4bf59fd346feab1a3b` |
| `judgments_sft2_samples.jsonl` | 2,706,261 | `7f362f638cf42c9a24424481f2afcfba3c698a59c9f8df42f8847d54de40a44f` |
| `judgments_sftbf16_samples.jsonl` | 2,737,340 | `c19c1f42ea6c2440cf089e0b153833b0ac73e433dfefa21d2f5124d7cec8ec30` |
| `judgments_small_selection.jsonl` | 1,421,658 | `e4bb29e6da751c0fd1c790a66951d9ca673da0cdb4b2c7e4ec97bb05ae881a6c` |
| `judgments_small_sft_k4.jsonl` | 2,768,162 | `96e41a5f8f60996557e4bfef2a60a325849bb09ee9741309a7bc3ebe3ce602ac` |
| `judgments_train_samples.jsonl` | 2,576,072 | `853ae447a2e9bd73c02c93aa2e7b807e6c6b1c7fa33fc6dc4524f9ea3bcc6930` |
| `pairs_train70.jsonl` | 3,197,904 | `98fed17aa44a257086606362c727fe75288a038758b1fa0c4d4dc24f34ba90fe` |
| `pairs_train70_expanded4.jsonl` | 15,111,507 | `9fdc1d0b4b24f4f9f5c481aa83e2e2d017bd03b7894a9454e28366b8510ed74d` |
| `pairs_train70_gemma-4-31b.jsonl` | 3,321,270 | `2bbc7a55f207db8746faa2a5fadf981f62097e804354e59ab34991c1b36842fa` |
| `pairs_train70_gemma-4-31b_expanded4.jsonl` | 20,536,160 | `61c7088d975203ec548cb31e70e6fcae2fd7a4b0d5b8b4a9c63c2eadb4a4c0fe` |
| `pairs_train70_gemma_maxgap.jsonl` | 6,913,748 | `03dddb02b37a7aedaefbe019a761f33951e4167298399585ce5a3e3e4777205c` |
| `pairs_train70_gemma_onpol.jsonl` | 783,409 | `e043635bd3abbebd81317001490b3b1abbc2f2482fb76a1372ac6ab21a0a3e80` |
| `pairs_train70_gemma_onpol_all.jsonl` | 2,451,112 | `21dc22a6be1866f55e869b253749bf680837fc3bdc5615ba1bf238637b1a4103` |
| `pairs_train70_sft2.jsonl` | 7,058,208 | `324fc4c389beea327dce57fc0894dddcd5119e7c3f6c759bb6daac307d2101d5` |
| `pairs_train70_sftbf16.jsonl` | 6,788,317 | `0d46cd54f2b0cfb3a871236f2eaf338535bd24b6518f813e5b20d1440ca24a37` |
| `pairs_train70_small_sft2.jsonl` | 13,862,115 | `0bb3259d8d2d790d62f12c46840f32d07d7fe800d23f897c1c3ec2bb6c6a7902` |
| `sft_train_guided.jsonl` | 2,338,030 | `9fe9920f04ab2f9c033f14d7abc38896f4e9b2b1a4ed965e2162bc25746cf53b` |
| `sft_train_small.jsonl` | 3,154,509 | `50a38095cc08a78462fc589bbc7b9e68ede1d5a4570736756d03edd9a7141d8d` |
| `sft_train_small_messages.jsonl` | 3,131,170 | `a02ccc02a0c792d716d55e8b42423e54e236740e7aee7d648f2dcb08ef706f8d` |
| `tinker-runs/dpo_small_sft2_run/config.json` | 1,231 | `0b2a06bb200460138eed0432435ef85421f370219e77bd60f8ec57d7d5157faa` |
| `tinker-runs/dpo_small_sft2_run/metrics.jsonl` | 64,568 | `26efd6f2e466e6e19af2974e4e1f7a11b418a9d17108f1660b8bc671b315644d` |
| `tinker-runs/dpo_small_sft2_sweep_lr0.0001/config.json` | 1,252 | `2cbf57ee52cca45843e87437caa7e221d07e4590a603ee67bfa83f0901c63680` |
| `tinker-runs/dpo_small_sft2_sweep_lr0.0001/metrics.jsonl` | 64,516 | `3f12c2609b7a91316e17f3f1cda9f403e42b8eafb3c34a212073663eebe98eff` |
| `tinker-runs/dpo_small_sft2_sweep_lr0.0001_ep3/config.json` | 1,260 | `b736928d8a67b76e36a0f0b88b2e89102365aab2d2af9f939fbc81072498d555` |
| `tinker-runs/dpo_small_sft2_sweep_lr0.0001_ep3/metrics.jsonl` | 194,267 | `5ee18a025058287f3da28b4c06f233a879f154f7d94d247817992b1034cf4928` |
| `tinker-runs/dpo_small_sft2_sweep_lr0.0003/config.json` | 1,252 | `99dfb90aad2a399d29cdfdc972079fe809e8e1b10c7226f68a18c06f579c02b7` |
| `tinker-runs/dpo_small_sft2_sweep_lr0.0003/metrics.jsonl` | 64,528 | `a8da96aefa8fdc0bb9255f037abeb8d96a06ffddd41a2c977e38579451533623` |
| `tinker-runs/dpo_small_sft2_sweep_lr1e-05_ep3/config.json` | 1,257 | `9a4d09245f78fbd59b36f09a4afaa493bb28df6aedeea8b8078e7c5d9ddc20f6` |
| `tinker-runs/dpo_small_sft2_sweep_lr1e-05_ep3/metrics.jsonl` | 193,834 | `acdaf88a0cb689f34ab42648039477e06977f4eab7d2d8f27420ca7edec94438` |
| `tinker-runs/dpo_small_sft2_sweep_lr3e-05/config.json` | 1,249 | `fe9400ce95dab09791f07a350b889b476f4924015259f3255db389befca2d1cf` |
| `tinker-runs/dpo_small_sft2_sweep_lr3e-05/metrics.jsonl` | 64,485 | `c845aebebaf8480da6110addfb02173f30dece631c44dc435594a36e32b64b30` |
| `tinker-runs/dpo_small_sft2_sweep_lr3e-05_ep3/config.json` | 1,257 | `901d31dc0eeec40c8c267dcc93676a04ebded70177097ee124a1230e1d26daf1` |
| `tinker-runs/dpo_small_sft2_sweep_lr3e-05_ep3/metrics.jsonl` | 194,067 | `fb6de6d6526c44710c1a273aa195fa508a899b0fe4da7dd57a45bafadb83d7fa` |
| `tinker-runs/run1/config.json` | 1,127 | `dfbbfccc37386bc34af054e451fce2ae8bfb6b755bf6c778aeb3abd32c78c4c3` |
| `tinker-runs/run1/metrics.jsonl` | 48,108 | `2767d40b902cd7b4901000f187185dffa5f9e5cdb570870f743b5b55519ce09a` |
| `tinker-runs/run2/config.json` | 1,138 | `19d4d0bab6e616ba9335466d307fa5d07311b7ab3ce52a15e432c9bc63df2c10` |
| `tinker-runs/run2/metrics.jsonl` | 57,226 | `0a9270dacc564531d25c5025558548b14e9f533507f12e85c754ceca727ec3ed` |
| `tinker-runs/sft_small_run/config.json` | 1,148 | `df3cd72e18874eece966efc79318a7b3626b25bd6780e5d45808b12eb9f05fba` |
| `tinker-runs/sft_small_run/metrics.jsonl` | 31,206 | `f268a72681b4d98346b92c3f89689dfbffd52d80449044187f1cac6109ca99d2` |
| `train_inputs_gemma.jsonl` | 330,473 | `3c6272cda756731a19fa472ff1b92fce6274bd149fc5611a9df95075d39aa954` |
| `train_log_bf16sft.jsonl` | 7,403 | `7ee2b4eb474b81d06ec64b5c6f42d7cf45d01ce5791ccd735fbea7f02b8ed560` |
| `train_log_maxgap.jsonl` | 7,166 | `5e52f67d0a2af61451d5851231bb60b76cea574f531549778b1dd9ad6154ab9c` |
| `train_log_onpol.jsonl` | 4,903 | `ef79c23d9768f219ef533d18319fcb84e9c5131bf2e7fa97579ab869910b44f5` |
| `train_log_sft.jsonl` | 7,393 | `80f7fc661602ae4c060758b25121971df8af685d79b9faa4c713cb284360fc38` |
| `train_log_sftdpo.jsonl` | 5,919 | `f0dbeb00392fba85f0ee245547e407e9458e69ef5cc186a604fa45247c2ad567` |

## jaleesbench-main-run.tar.gz — the benchmark main run the builders read (extracted to `jaleesbench/results/`)

5 members, 110,856,255 bytes compressed.

| member | bytes | sha256 |
|---|---:|---|
| `NOTICE` | 1,088 | `1587f180062c5860b0df5c91d7bafe0da1cce0bad59ff56d35a540d93016e365` |
| `citations_llm.jsonl` | 5,379,636 | `1b345305503e794f16187aa42fb3fc3025eac321a7cbc200eccd1378787eb076` |
| `collect.jsonl` | 280,896,403 | `5dcd0b952e9a80270bf5d27369ef80f7c4f9dc1b7e457e90751b0723ac9a055f` |
| `judgments.jsonl` | 236,085,273 | `a6fcada7bc472fa964cc229c2e42c8626def8628f7fef274d7a8eb3dc59b7946` |
| `judgments_v2.jsonl` | 158,406 | `e3dd76b23184548d1dd3faa931e7e56f674cc10c65413cc102d616accf8977ef` |

