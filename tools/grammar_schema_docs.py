"""Generate the grammar JSON field catalog directly from schema.json (one source of truth)."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=ROOT/'content/grammar/schema.json'
OUT=ROOT/'docs/grammar_fields.md'


def dtype(item):
    if '$ref' in item: return item['$ref'].rsplit('/',1)[-1]
    if 'enum' in item:return ' / '.join(map(str,item['enum']))
    if 'oneOf' in item:return ' или '.join(dtype(t) for t in item['oneOf'])
    if 'allOf' in item:return ' + '.join(dtype(t) for t in item['allOf'])
    typ=item.get('type','object')
    if typ=='array':return 'массив ['+dtype(item.get('items',{}))+']'
    if typ=='object':return 'объект / словарь' if 'additionalProperties' in item and item['additionalProperties'] else 'объект'
    return {'string':'строка','integer':'целое число','boolean':'логическое','number':'число'}.get(typ,typ)


def generate():
    schema=json.loads(SCHEMA.read_text(encoding='utf8'))
    lines=['# Справочник JSON отдельного курса испанской грамматики','',
           '> Автоматически сформировано из `content/grammar/schema.json`. Для обновления: `python tools/grammar_schema_docs.py`.','',
           'Все описанные объекты запрещают неизвестные поля, кроме намеренно открытых словарей (`answerWarnings`, `portraits`, `optionLabels`).',
           'Схема описывает **текущий** движок. Новые форматы сначала требуют расширения схемы и тестов, но не изменения старых `id` или строк `answers`.','']
    for name,defn in schema['$defs'].items():
        lines+=['## '+name,'',defn.get('description',''),'', '| Поле | Тип | Обязательно |', '|---|---|---|']
        required=set(defn.get('required',[]))
        for key,item in defn.get('properties',{}).items():
            lines.append(f"| `{key}` | {dtype(item)} | {'да' if key in required else 'нет'} |")
        lines+=['']
    lines+=['## Реально поддерживаемые вопросы','',
            'Режим определяется фактическими полями — добавлять новый обязательный `type` на этом этапе **нельзя**:',
            '- **Выбор**: `options` (обычный или `interaction: "gap-choice"`), все допустимые `answers` должны присутствовать в `options`.',
            '- **Свободный ввод**: `answers` + при необходимости `inputFormat`, `gapParts`, `gapWordCounts`.',
            '- **Несколько вводимых пропусков**: `gapParts` имеет N+1 частей, `gapWordCounts` — N положительных чисел, сумма равна словам первого ответа.',
            '- **Выбор в пропусках**: `guidedGaps.parts` (N+1), `guidedGaps.choices` (N списков); у текущих вопросов допускаются одновременно `options` и `interaction: "gap-choice"`.',
            '- **Сборка фразы**: `interaction: "build"` + `tiles`. Есть совместимые исторические `build` + `guidedGaps`; см. существующий юнит 17.',
            '- **Артикль**: `interaction: "article-input"` без `options`/`tiles`; контроль отсутствия артикля управляется `allowNoArticle`.',
            '- **Контекст и наглядность**: `clues`, `translation`, `facts`, `ratings`, `clock`, `distance`, `sourceParts`, `image`, `imageAlt`, `pictureCount` — самостоятельные данные, а не новый тип ответа.',
            '', '### Пример: вопрос с альтернативными правильными ответами','',
            '```json','{ "prompt": "Назови форму", "answers": ["rubíes", "rubís"], "explain": "Обе нормативные формы допустимы." }','```','',
            '### Пример: упражнение и связь с теорией','',
            '```json', '{ "id": "new.1", "title": "Практика", "instruction": "Дополни предложения.", "theorySections": [0], "questions": [{"prompt": "___", "answers": ["casa"], "explain": "Существительное женского рода."}] }', '```','',
            '**Не копируйте этот пример как полноценный готовый юнит** — у юнита дополнительно обязательны `number`, `id`, `title`, `subtitle`, `level`, `sections`, `summary`, `exercises`, `learningOrder`.','',
            '### Совместимость и миграции','',
            'Значения `unit.id` и `group.id`, порядок вопросов и существующие строки `answers` используются в ключах прогресса. Ни линтер, ни схема их не изменяют.',
            'При изменении смысла вопроса должна меняться `revision` группы в соответствии с действующим гайдом. Политика трёх жизней и ударений не меняется.',
            '', '### Добавление нового типа','',
            'Сначала отдельная задача на движок и оценивание, затем фикстура с допустимыми и недопустимыми сочетаниями, расширение `schema.json`, обновление соответствующих правил `grammar_quality.py`, регрессионные тесты в Python и браузере. После этого перегенерировать справочник.','']
    return '\n'.join(lines)

if __name__=='__main__':
    import sys
    content=generate()
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding='utf-8')!=content:
            print('Outdated documentation: run python tools/grammar_schema_docs.py')
            raise SystemExit(1)
        print('Schema documentation matches')
    else:
        OUT.write_text(content,encoding='utf-8')
        print('Written',OUT)
