# Справочник JSON отдельного курса испанской грамматики

> Автоматически сформировано из `content/grammar/schema.json`. Для обновления: `python tools/grammar_schema_docs.py`.

Все описанные объекты запрещают неизвестные поля, кроме намеренно открытых словарей (`answerWarnings`, `portraits`, `optionLabels`).
Схема описывает **текущий** движок. Новые форматы сначала требуют расширения схемы и тестов, но не изменения старых `id` или строк `answers`.

## unit

Один файл JSON = один самостоятельный грамматический юнит.

| Поле | Тип | Обязательно |
|---|---|---|
| `id` | строка | да |
| `number` | целое число | да |
| `title` | строка | да |
| `subtitle` | строка | да |
| `level` | строка | да |
| `sections` | массив [section] | да |
| `exercises` | массив [group + объект] | да |
| `summary` | summary | да |
| `learningOrder` | массив [строка] | да |
| `revision` | целое число | нет |

## section



| Поле | Тип | Обязательно |
|---|---|---|
| `title` | строка | да |
| `paragraphs` | массив [строка] | да |
| `check` | group | да |
| `presentation` | строка | нет |
| `wordGroups` | массив [wordGroup] | нет |
| `dialogues` | массив [dialogue] | нет |
| `table` | table | нет |
| `illustration` | illustration | нет |
| `schemes` | массив [scheme] | нет |
| `notes` | массив [строка] | нет |
| `examples` | массив [массив [строка]] | нет |
| `formulas` | массив [строка] | нет |
| `schemeGrid` | логическое | нет |
| `agreement` | массив [scheme] | нет |
| `distanceMap` | объект | нет |

## group



| Поле | Тип | Обязательно |
|---|---|---|
| `id` | строка | да |
| `title` | строка | да |
| `instruction` | строка | да |
| `questions` | массив [question] | да |
| `theorySections` | массив [целое число] | нет |
| `inputLabel` | строка | нет |
| `preview` | preview | нет |
| `inputFormat` | inputFormat | нет |
| `inlineAnswer` | логическое | нет |
| `phraseInput` | логическое | нет |
| `limitedAttempt` | логическое | нет |
| `answerPlaceholder` | строка | нет |
| `allowNoArticle` | логическое | нет |
| `revision` | целое число | нет |
| `pictureTitle` | строка | нет |
| `introGroups` | массив [wordGroup] | нет |
| `vocabulary` | table | нет |
| `articleContractions` | логическое | нет |
| `accentSensitive` | логическое | нет |
| `family` | family | нет |
| `example` | объект | нет |
| `questionBlocks` | массив [объект] | нет |
| `deferAnswerFeedback` | логическое | нет |
| `shuffleOptions` | логическое | нет |
| `optionOrderReason` | строка | нет |
| `accentPolicy` | strict / soft / contextual | нет |
| `accentContrasts` | массив [accentContrast] | нет |

## question

Один вопрос; id не вводится: индекс вопроса сохраняет идентичность попытки.

| Поле | Тип | Обязательно |
|---|---|---|
| `prompt` | строка | да |
| `answers` | массив [строка] | да |
| `explain` | строка | да |
| `context` | строка | нет |
| `sourceRef` | строка | нет |
| `inputChars` | массив [á / é / í / ó / ú / ü / ñ] | нет |
| `options` | массив [строка] | нет |
| `inputFormat` | inputFormat | нет |
| `optionLabels` | объект / словарь | нет |
| `shuffleOptions` | логическое | нет |
| `optionOrderReason` | строка | нет |
| `interaction` | choice / gap-choice / input / article-input / build | нет |
| `translation` | строка | нет |
| `learningAction` | строка | нет |
| `facts` | facts | нет |
| `sourceParts` | массив [строка] | нет |
| `tiles` | массив [строка] | нет |
| `gapParts` | массив [строка] | нет |
| `sourceLabel` | строка | нет |
| `gapWordCounts` | массив [целое число] | нет |
| `feedbackAnswers` | массив [строка] | нет |
| `clues` | массив [массив [строка]] | нет |
| `image` | строка | нет |
| `imageAlt` | строка | нет |
| `answerHint` | строка | нет |
| `answerWarnings` | объект / словарь | нет |
| `distance` | near / listener / far | нет |
| `clock` | объект | нет |
| `accentSensitive` | логическое | нет |
| `pictureCount` | целое число | нет |
| `guidedGaps` | guidedGaps | нет |
| `ratings` | ratings | нет |
| `retryHint` | строка | нет |
| `accentPolicy` | strict / soft / contextual | нет |
| `accentContrasts` | массив [accentContrast] | нет |
| `normalize` | phrase | нет |
| `gapAnswers` | массив [массив [строка]] | нет |

## wordGroup



| Поле | Тип | Обязательно |
|---|---|---|
| `title` | строка | да |
| `words` | массив [массив [строка]] | да |
| `label` | строка | нет |
| `exception` | логическое | нет |

## table



| Поле | Тип | Обязательно |
|---|---|---|
| `heads` | массив [строка] | да |
| `rows` | массив [массив [строка]] | да |
| `compactForms` | логическое | нет |

## scheme



| Поле | Тип | Обязательно |
|---|---|---|
| `label` | строка | да |
| `from` | строка или массив [строка] | да |
| `to` | строка или массив [строка] | да |
| `note` | строка | нет |
| `fromLabel` | строка | нет |
| `toLabel` | строка | нет |
| `translations` | массив [массив [строка]] | нет |
| `change` | объект | нет |
| `inlineTranslation` | логическое | нет |

## illustration



| Поле | Тип | Обязательно |
|---|---|---|
| `image` | строка | да |
| `alt` | строка | да |
| `examples` | массив [массив [строка]] | да |
| `captionExamples` | логическое | нет |
| `captionDialogue` | логическое | нет |

## dialogue



| Поле | Тип | Обязательно |
|---|---|---|
| `title` | строка | да |
| `lines` | массив [массив [строка]] | да |

## ratings



| Поле | Тип | Обязательно |
|---|---|---|
| `label` | строка | да |
| `people` | массив [объект] | да |

## facts



| Поле | Тип | Обязательно |
|---|---|---|
| `label` | строка | да |
| `items` | массив [массив [строка]] | да |

## guidedGaps



| Поле | Тип | Обязательно |
|---|---|---|
| `parts` | массив [строка] | да |
| `choices` | массив [массив [строка]] | да |

## warning



| Поле | Тип | Обязательно |
|---|---|---|
| `preferred` | строка | да |
| `message` | строка | да |
| `explanation` | строка | да |
| `source` | строка | да |

## preview



| Поле | Тип | Обязательно |
|---|---|---|
| `source` | строка | да |
| `answer` | строка | да |
| `translation` | строка | да |
| `targetPrefix` | строка | нет |
| `sentenceParts` | массив [строка] | нет |
| `tip` | строка | нет |
| `displayAnswer` | строка | нет |
| `gapParts` | массив [строка] | нет |
| `gapAnswers` | массив [строка] | нет |

## inputFormat



| Поле | Тип | Обязательно |
|---|---|---|
| `instruction` | строка | да |
| `placeholder` | строка | да |
| `example` | строка | нет |

## family



| Поле | Тип | Обязательно |
|---|---|---|
| `parents` | массив [строка] | да |
| `branches` | массив [объект] | да |
| `portraits` | объект / словарь | да |

## summary

Итоговые схемы, словарные группы либо таблица.

| Поле | Тип | Обязательно |
|---|---|---|
| `wordGroups` | массив [wordGroup] | нет |
| `heads` | массив [строка] | нет |
| `rows` | массив [массив [строка]] | нет |
| `schemes` | массив [scheme] | нет |
| `topicMap` | topicMap | нет |

## accentContrast

Подтверждённая в контексте пара разных грамматических значений.

| Поле | Тип | Обязательно |
|---|---|---|
| `expected` | строка | да |
| `entered` | строка | да |
| `explanation` | строка | да |

## topicMap

Адаптивная карта только итогового слайда; основная таблица summary остаётся запасным представлением.

| Поле | Тип | Обязательно |
|---|---|---|
| `lead` | строка | да |
| `formula` | массив [массив [строка]] | да |
| `cards` | массив [topicMapCard] | да |
| `takeaway` | строка | да |

## topicMapCard



| Поле | Тип | Обязательно |
|---|---|---|
| `title` | строка | да |
| `tone` | violet / peach / mint / blue / rose | да |
| `text` | строка | нет |
| `pairs` | массив [массив [строка]] | нет |
| `chips` | массив [строка] | нет |
| `examples` | массив [массив [строка]] | нет |
| `illustrationSection` | целое число | нет |
| `note` | строка | нет |
| `pairStyle` | columns / stacked | нет |

## Реально поддерживаемые вопросы

Режим определяется фактическими полями — добавлять новый обязательный `type` на этом этапе **нельзя**:
- **Выбор**: `options` (обычный или `interaction: "gap-choice"`), все допустимые `answers` должны присутствовать в `options`.
- **Свободный ввод**: `answers` + при необходимости `inputFormat`, `gapParts`, `gapWordCounts`.
- **Несколько вводимых пропусков**: `gapParts` имеет N+1 частей, `gapWordCounts` — N положительных чисел, сумма равна словам первого ответа.
- **Выбор в пропусках**: `guidedGaps.parts` (N+1), `guidedGaps.choices` (N списков); у текущих вопросов допускаются одновременно `options` и `interaction: "gap-choice"`.
- **Сборка фразы**: `interaction: "build"` + `tiles`. Есть совместимые исторические `build` + `guidedGaps`; см. существующий юнит 17.
- **Артикль**: `interaction: "article-input"` без `options`/`tiles`; контроль отсутствия артикля управляется `allowNoArticle`.
- **Контекст и наглядность**: `clues`, `translation`, `facts`, `ratings`, `clock`, `distance`, `sourceParts`, `image`, `imageAlt`, `pictureCount` — самостоятельные данные, а не новый тип ответа.

### Пример: вопрос с альтернативными правильными ответами

```json
{ "prompt": "Назови форму", "answers": ["rubíes", "rubís"], "explain": "Обе нормативные формы допустимы." }
```

### Пример: упражнение и связь с теорией

```json
{ "id": "new.1", "title": "Практика", "instruction": "Дополни предложения.", "theorySections": [0], "questions": [{"prompt": "___", "answers": ["casa"], "explain": "Существительное женского рода."}] }
```

**Не копируйте этот пример как полноценный готовый юнит** — у юнита дополнительно обязательны `number`, `id`, `title`, `subtitle`, `level`, `sections`, `summary`, `exercises`, `learningOrder`.

### Совместимость и миграции

Значения `unit.id` и `group.id`, порядок вопросов и существующие строки `answers` используются в ключах прогресса. Ни линтер, ни схема их не изменяют.
При изменении смысла вопроса должна меняться `revision` группы в соответствии с действующим гайдом. Политика трёх жизней и ударений не меняется.

### Добавление нового типа

Сначала отдельная задача на движок и оценивание, затем фикстура с допустимыми и недопустимыми сочетаниями, расширение `schema.json`, обновление соответствующих правил `grammar_quality.py`, регрессионные тесты в Python и браузере. После этого перегенерировать справочник.
