"""Schema checks and non-blocking teaching-quality diagnostics for standalone grammar.

Data are read without rendering or changing question order, answers or progress keys.
Structure is strict, pedagogy is deliberately heuristic and requires teacher review.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

from jsonschema import Draft202012Validator

DIRECTORY = Path(__file__).resolve().parent.parent / 'content' / 'grammar'
SCHEMA_FILE = DIRECTORY / 'schema.json'
ALLOW_FILE = DIRECTORY / 'lint_allow.json'
SEVERITIES = ('ERROR', 'WARNING', 'INFO')


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    unit: int | None
    group: str | None
    question: int | None
    message: str
    reason: str
    recommendation: str
    file: str
    baseline: bool = False

    @property
    def fingerprint(self) -> str:
        identity = f'{self.file}|{self.rule}|{self.group or ""}|{self.question or 0}|{self.message}'
        return hashlib.sha256(identity.encode('utf-8')).hexdigest()[:20]

    def to_dict(self) -> dict:
        return dict(**asdict(self), fingerprint=self.fingerprint)


def schema_validator(directory: Path = DIRECTORY) -> Draft202012Validator:
    source = directory / 'schema.json' if (directory / 'schema.json').exists() else SCHEMA_FILE
    schema = json.loads(source.read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _issue(severity: str, rule: str, unit: dict | None, file: str,
           message: str, reason: str, recommendation: str,
           group: str | None = None, question: int | None = None) -> Finding:
    return Finding(severity, rule, unit.get('number') if isinstance(unit, dict) and
                   isinstance(unit.get('number'), int) else None,
                   group, question, message, reason, recommendation, file)


def structure_unit(unit: dict, file: str, validator: Draft202012Validator) -> list[Finding]:
    """Static schema + checks involving multiple fields and question formats."""
    found = []
    for error in sorted(validator.iter_errors(unit), key=lambda e: (list(map(str, e.absolute_path)), e.message)):
        path = '/'.join(map(str, error.absolute_path)) or '<unit>'
        found.append(_issue('ERROR', 'SCHEMA', unit, file, f'{path}: {error.message}',
                            'JSON нарушает документированный контракт данных.',
                            'Исправить поле по content/grammar/schema.json; не переименовывать существующие id или ответы.'))
    if not isinstance(unit, dict) or not isinstance(unit.get('sections'), list) or not isinstance(unit.get('exercises'), list):
        return found
    sections = unit['sections']
    groups = [(s.get('check'), i, True) for i, s in enumerate(sections) if isinstance(s, dict) and isinstance(s.get('check'), dict)]
    groups += [(g, None, False) for g in unit['exercises'] if isinstance(g, dict)]
    all_ids: set[str] = set()
    for group, section_idx, is_check in groups:
        name = group.get('id')
        if not isinstance(name, str):
            continue
        if name in all_ids:
            found.append(_issue('ERROR', 'DUPLICATE_GROUP', unit, file, f'Повторяется id {name!r}.',
                                'Прогресс двух групп будет использовать одинаковый ключ.',
                                'Сохранить существующий id и устранить конфликт только у новой группы.', name))
        all_ids.add(name)
        refs = group.get('theorySections')
        if not is_check and not refs:
            found.append(_issue('ERROR', 'MISSING_THEORY_LINK', unit, file, 'Упражнение не связано с теорией.',
                                'При ошибке неизвестно, к какому правилу направить ученика.',
                                'Указать непустой theorySections с индексами подходящих разделов.', name))
        if refs is not None:
            if not isinstance(refs, list) or not refs or any(type(i) is not int or not 0 <= i < len(sections) for i in refs) or len(refs) != len(set(map(str, refs))):
                found.append(_issue('ERROR', 'BROKEN_THEORY_LINK', unit, file, 'Некорректные theorySections.',
                                    'Ссылка не указывает на существующие разные теоретические разделы.',
                                    'Исправить индексы в пределах sections; не изменять id.', name))
        if is_check and section_idx is not None and refs is not None and section_idx not in refs:
            found.append(_issue('WARNING', 'CHECK_THEORY_SCOPE', unit, file, 'Мини-проверка не связана со своим разделом.',
                                'Связь указывает только на другие теоретические блоки.',
                                'Проверить учебный замысел и добавить текущий раздел при необходимости.', name))
        for index, q in enumerate(group.get('questions', []) if isinstance(group.get('questions'), list) else [], 1):
            if not isinstance(q, dict):
                continue
            answers = q.get('answers', [])
            options = q.get('options')
            tiles = q.get('tiles')
            guided = q.get('guidedGaps')
            gap_parts = q.get('gapParts')
            mode = q.get('interaction')
            if isinstance(answers, list) and all(isinstance(a,str) for a in answers) and isinstance(options, list) and all(isinstance(o,str) for o in options) and not set(answers).issubset(options):
                found.append(_issue('ERROR', 'UNAVAILABLE_ANSWER', unit, file, 'Верный ответ отсутствует среди вариантов.',
                                    'Нельзя выбрать правильный ответ из options.', 'Добавить верную форму в options.', name, index))
            if options is not None and (tiles is not None or gap_parts is not None or (guided is not None and mode != 'gap-choice')):
                found.append(_issue('ERROR', 'CONFLICTING_INPUT', unit, file, 'Несовместимые способы ввода в одном вопросе.',
                                    'Одновременно переданы options и составные элементы другого формата.',
                                    'Оставить один поддерживаемый формат задания.', name, index))
            if tiles is not None and (mode != 'build' or not isinstance(tiles, list) or not isinstance(answers, list)
                                      or not answers or Counter(answers[0].split()) - Counter(tiles)):
                found.append(_issue('ERROR', 'UNBUILDABLE_ANSWER', unit, file, 'Сборка из плиток не позволяет получить первый правильный ответ.',
                                    'Банк tiles несовместим с interaction: build или не содержит необходимых слов.',
                                    'Проверить порядок и количество плиток без изменения существующих answers.', name, index))
            if mode == 'build' and tiles is None and guided is None:
                found.append(_issue('ERROR', 'UNSUPPORTED_BUILD', unit, file, 'interaction: build без плиток или guidedGaps.',
                                    'Плееру не из чего собирать ответ.', 'Добавить tiles или выбрать режим ввода.', name, index))
            if mode == 'article-input' and any(x is not None for x in (options, tiles, guided, gap_parts)):
                found.append(_issue('ERROR', 'ARTICLE_INPUT_CONFLICT', unit, file, 'article-input смешан с выбором/плитками/пропусками.',
                                    'Специальное поле короткого артикля не поддерживает такие сочетания.',
                                    'Удалить конфликтующий параметр или выбрать другой режим.', name, index))
            if isinstance(gap_parts, list):
                counts = q.get('gapWordCounts')
                gaps = len(gap_parts) - 1
                if gaps < 1 or (counts is not None and (not isinstance(counts, list) or len(counts) != gaps or
                               not all(type(n) is int and n > 0 for n in counts) or
                               not answers or sum(counts) != len(answers[0].split()))):
                    found.append(_issue('ERROR', 'GAP_ARITY', unit, file, 'Число пропусков не соответствует gapWordCounts/answers.',
                                        'Отрисованные поля не могут получить полный ожидаемый ответ.',
                                        'Согласовать gapParts, gapWordCounts и answers.', name, index))
            if isinstance(guided, dict):
                parts, choices = guided.get('parts'), guided.get('choices')
                if not isinstance(parts, list) or not isinstance(choices, list) or len(parts) != len(choices) + 1:
                    found.append(_issue('ERROR', 'GUIDED_ARITY', unit, file, 'Число частей guidedGaps неверно.',
                                        'Для N списков вариантов нужны N+1 текстовых частей.',
                                        'Привести parts и choices к согласованному количеству.', name, index))
            # Stage 3: contextual accent decisions must be justified by question data.
            policy = q.get('accentPolicy', group.get('accentPolicy'))
            contrasts = list(group.get('accentContrasts') or []) + list(q.get('accentContrasts') or [])
            if policy == 'contextual' and not contrasts:
                found.append(_issue('ERROR', 'ACCENT_CONTEXT_MISSING', unit, file,
                                    'Контекстный режим без указанных грамматических противопоставлений.',
                                    'Движок не должен угадывать значение пропущенного ударения.',
                                    'Добавить accentContrasts или выбрать strict/soft.', name, index))
            if policy == 'soft' and q.get('accentSensitive') is True:
                found.append(_issue('ERROR', 'ACCENT_POLICY_CONFLICT', unit, file,
                                    'Одновременно заданы мягкий и строгий режимы.',
                                    'Проверка не должна зависеть от противоречивой конфигурации.',
                                    'Оставить один явный режим.', name, index))
            if contrasts and isinstance(answers, list):
                tokens = {token.casefold() for answer in answers if isinstance(answer, str)
                          for token in re.findall(r'\w+', answer, flags=re.UNICODE)}
                for pair in contrasts:
                    if not isinstance(pair, dict):
                        continue  # JSON Schema reports the invalid structure.
                    expected, entered = pair.get('expected', ''), pair.get('entered', '')
                    if isinstance(expected, str) and expected.casefold() not in tokens:
                        found.append(_issue('ERROR', 'ACCENT_CONTRAST_UNUSED', unit, file,
                                            f'Контраст {expected!r} отсутствует в допустимых ответах.',
                                            'Контекстный запрет никогда не сработает.',
                                            'Сверить пару с answers, не придумывая новые варианты.', name, index))
                    if isinstance(expected, str) and isinstance(entered, str):
                        trans = str.maketrans('áéíóúÁÉÍÓÚ', 'aeiouAEIOU')
                        if expected == entered or expected.translate(trans).casefold() != entered.translate(trans).casefold():
                            found.append(_issue('ERROR', 'ACCENT_CONTRAST_INVALID', unit, file,
                                                f'Пара {expected!r}/{entered!r} отличается не только акутом.',
                                                'Контекстный режим описывает лишь отсутствие/наличие ударения.',
                                                'Уточнить expected и entered.', name, index))
            if q.get('gapAnswers') is not None:
                count = len(gap_parts)-1 if isinstance(gap_parts, list) else len((guided or {}).get('choices', [])) if isinstance(guided, dict) else 0
                if len(q['gapAnswers']) != count:
                    found.append(_issue('ERROR', 'GAP_ANSWERS_ARITY', unit, file,
                                        'Число списков gapAnswers не совпадает с числом пропусков.',
                                        'Нельзя точно сопоставить варианты ответов с полями.',
                                        'Для N полей задать N списков, не меняя общий answers.', name, index))
                if (isinstance(gap_parts, list) and len(q['gapAnswers']) == count and
                        isinstance(answers, list) and all(isinstance(a, str) for a in answers)):
                    widths = q.get('gapWordCounts') or [1] * count
                    if (isinstance(widths, list) and len(widths) == count and
                            all(isinstance(n, int) and n > 0 for n in widths) and
                            all(len(a.split()) == sum(widths) for a in answers)):
                        expected_slots = [set() for _ in range(count)]
                        for answer in answers:
                            words = answer.split()
                            pos = 0
                            for slot, width in enumerate(widths):
                                expected_slots[slot].add(' '.join(words[pos:pos+width]))
                                pos += width
                        for slot, allowed in enumerate(q['gapAnswers']):
                            if isinstance(allowed, list) and set(allowed) != expected_slots[slot]:
                                found.append(_issue('ERROR', 'GAP_ANSWERS_INCONSISTENT', unit, file,
                                                    f'У пропуска {slot+1} варианты расходятся с полным answers.',
                                                    'Подсказка не может принимать или показывать несуществующие комбинации.',
                                                    'Согласовать gapAnswers с исходными answers.', name, index))
            if 'pictureCount' in q and not q.get('image'):
                found.append(_issue('ERROR', 'MISSING_PICTURE', unit, file, 'pictureCount без изображения.',
                                    'Отрисовка картинки не сможет работать.', 'Добавить image и imageAlt.', name, index))
            if q.get('image') and not q.get('imageAlt'):
                found.append(_issue('ERROR', 'MISSING_IMAGE_ALT', unit, file, 'Для изображения отсутствует imageAlt.',
                                    'Нарушена доступность и не описана ситуация ученику.', 'Добавить содержательное alt-описание.', name, index))
    order = unit.get('learningOrder')
    if order is not None:
        routes = {f'section:{i}' for i in range(len(sections))} | {'summary'} | {f'exercise:{g.get("id")}' for g in unit['exercises'] if isinstance(g, dict)}
        if not isinstance(order, list) or len(order) != len(routes) or set(order) != routes:
            found.append(_issue('ERROR', 'BROKEN_LEARNING_ORDER', unit, file, 'learningOrder пропускает или повторяет этап.',
                                'Маршрут урока больше не соответствует sections, exercises и summary.',
                                'Синхронизировать маршрут, сохранив ключи групп.'))
    return found


def inspect_directory(directory: Path = DIRECTORY, only: set[int] | None = None, *, pedagogical: bool = True) -> list[Finding]:
    validator = schema_validator(directory)
    found = []
    # Sidecar policies are applied for the official course only, after raw JSON has
    # been inspected. This validates the same effective data the browser receives.
    from .grammar import apply_accent_policies
    policies = {}
    if directory.resolve() == DIRECTORY.resolve():
        policy_file = directory / 'accent_policies.json'
        if policy_file.is_file():
            try:
                policies = json.loads(policy_file.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError) as exc:
                found.append(_issue('ERROR', 'ACCENT_POLICY_PARSE', None, policy_file.name,
                                    'Невозможно прочитать каталог режимов ударений.', str(exc),
                                    'Исправить JSON каталога политик.'))
            if not isinstance(policies, dict):
                found.append(_issue('ERROR', 'ACCENT_POLICY_TYPE', None, policy_file.name,
                                    'Каталог режимов ударений должен быть словарём.',
                                    'Данные нельзя безопасно сопоставить с юнитами.',
                                    'Исправить структуру каталога.'))
                policies = {}
    seen_policy_units = set()
    seen: set[str] = set()
    seen_numbers: set[int] = set()
    for path in sorted(directory.glob('[0-9]*.json')):
        try:
            unit = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, UnicodeError) as exc:
            found.append(_issue('ERROR','JSON_PARSE',None,path.name,'Невозможно прочитать JSON.',str(exc),'Исправить синтаксис или кодировку.'))
            continue
        if not isinstance(unit, dict):
            found.extend(structure_unit(unit,path.name,validator))
            continue
        if only and unit.get('number') not in only:
            continue
        stable_id = unit.get('id') if isinstance(unit.get('id'),str) else '<invalid-id>'
        if stable_id in seen:
            found.append(_issue('ERROR','DUPLICATE_UNIT',unit,path.name,'Повторяется unit.id.',
                                'Прогресс разных юнитов окажется общим.','Уникализировать id только у нового юнита.'))
        seen.add(stable_id)
        if isinstance(unit.get('number'),int):
            if unit['number'] in seen_numbers:
                found.append(_issue('ERROR','DUPLICATE_UNIT_NUMBER',unit,path.name,'Повторяется номер юнита.',
                                    'Каталог не может однозначно сопоставить номер и урок.','Присвоить новый номер только новому уроку.'))
            seen_numbers.add(unit['number'])
        if isinstance(unit.get('id'),str) and unit['id']!=path.stem:
            found.append(_issue('INFO','FILE_ID_MISMATCH',unit,path.name,'Имя файла и unit.id отличаются.',
                                'Старые файлы могут иметь исторические имена; это не ошибка идентификатора.',
                                'Для новых юнитов назвать файл по id. Существующие id и ключи прогресса не менять.'))
        found.extend(structure_unit(unit,path.name,validator))
        policy = policies.get(unit.get('id'), {})
        if policy:
            seen_policy_units.add(unit['id'])
            try:
                apply_accent_policies(unit, policy, path)
            except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
                found.append(_issue('ERROR', 'ACCENT_POLICY_REFERENCE', unit, path.name,
                                    'Каталог ссылается на неподходящий вопрос или ответ.', str(exc),
                                    'Исправить ссылку на существующий unit/group/index без изменения id.'))
            else:
                found.extend(structure_unit(unit,path.name,validator))
        if pedagogical:
            found.extend(pedagogical_unit(unit,path.name))
    for missing in set(policies) - seen_policy_units if only is None else set():
        found.append(_issue('ERROR', 'ACCENT_POLICY_ORPHAN', None, 'accent_policies.json',
                            f'Каталог содержит неизвестный юнит {missing}.',
                            'Контекстное правило нельзя применить к существующему заданию.',
                            'Удалить устаревшую ссылку или восстановить корректную.'))
    return apply_baseline(found,directory)


def apply_baseline(findings: list[Finding], directory: Path = DIRECTORY) -> list[Finding]:
    path = directory / 'lint_allow.json'
    approved = {}
    if path.exists():
        raw=json.loads(path.read_text(encoding='utf-8'))
        for category in ('knownErrors','acceptedWarnings'):
            for entry in raw.get(category,[]):
                if isinstance(entry,dict) and isinstance(entry.get('fingerprint'),str) and len(entry.get('reason','').strip())>=15:
                    approved[entry['fingerprint']]=category
    return [Finding(**{**asdict(x),'baseline':x.fingerprint in approved and
                       (approved[x.fingerprint]=='knownErrors')==(x.severity=='ERROR')}) for x in findings]


def breaking_findings(findings: Iterable[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity=='ERROR' and not f.baseline]


def _mode(q: dict) -> str:
    if q.get('guidedGaps'): return 'guided-choice'
    if q.get('tiles'): return 'build'
    if q.get('options'): return 'choice'
    if q.get('gapParts'): return 'gaps-input'
    return 'input'


def _norm(s: str) -> str:
    return ' '.join(re.sub(r'[^\wñáéíóúü]+',' ',s.lower(),flags=re.UNICODE).split())


def pedagogical_unit(unit: dict, file: str) -> list[Finding]:
    """Conservative prompts for teacher review, never claims of grammatical proof."""
    out=[]
    def note(level, rule, msg, reason, action, group=None, qi=None):
        out.append(_issue(level,rule,unit,file,msg,reason,action,group,qi))
    exercise_modes=[]
    for group in [s['check'] for s in unit.get('sections',[]) if s.get('check')]+unit.get('exercises',[]):
        if not isinstance(group,dict):continue
        gid=group.get('id','?'); qs=group.get('questions',[])
        check=gid.startswith('check') or group.get('title')=='Мини-проверка'
        if check and (len(qs)<3 and all(_mode(q)=='choice' for q in qs)):
            note('WARNING','SHORT_CHECK',f'Мини-проверка: {len(qs)} вопроса/вопросов только с выбором.',
                 'Отгадывание не доказывает самостоятельное применение правила.',
                 'Обсудить добавление короткого ввода или контрастной ситуации; два вопроса сами по себе не ошибка.',gid)
        if check and not str(group.get('instruction','')).strip():
            note('INFO','EMPTY_CHECK_INSTRUCTION','Мини-проверка без отдельной инструкции.',
                 'Ученик получает меньше контекста о требуемом действии.','Добавить короткую понятную инструкцию.',gid)
        if not qs:continue
        modes=[_mode(q) for q in qs]
        if not check:exercise_modes.extend(modes)
        run=max((sum(1 for _ in v) for _,v in __import__('itertools').groupby(modes)),default=0)
        if len(qs)>=8 and run>=8:
            note('WARNING','LONG_MODE_RUN',f'{run} последовательных вопросов в формате {Counter(modes).most_common(1)[0][0]}.',
                 'Длинная серия повторяет одно действие, хотя закрепление иногда этого требует.',
                 'Проверить чередование распознавания, ввода и преобразования; не сокращать автоматически.',gid)
        if len(qs)>20 and len(set(modes))<2:
            note('WARNING','LONG_HOMOGENEOUS',f'{len(qs)} однотипных вопросов.',
                 'Упражнение длинное без смены формата; длина сама по себе не критическая ошибка.',
                 'Проверить разнообразие грамматических случаев и разделение по смыслу.',gid)
        counts=Counter(q['answers'][0] for q in qs if q.get('answers'))
        if len(qs)>=6:
            ans,n=counts.most_common(1)[0]
            if n/len(qs)>=.50:
                note('WARNING','DOMINANT_ANSWER',f'Ответ {ans!r} правильный в {n}/{len(qs)} вопросах.',
                     'Шаблон ответа может угадываться по частоте без применения правила.',
                     'Проверить необходимость контрастных случаев; не изменять корректные ответы ради статистики.',gid)
        wrong_usage=Counter()
        correct_usage=Counter()
        positions=[]
        for q in qs:
            if 'options' in q and q.get('answers'):
                for op in q['options']:
                    wrong_usage[op]+=1
                for ans in q['answers']:
                    if ans in q['options']:correct_usage[ans]+=1
                positions.append(q['options'].index(q['answers'][0])+1 if q['answers'][0] in q['options'] else None)
        for option,n in wrong_usage.items():
            if n>=5 and correct_usage[option]==0:
                note('WARNING','NEVER_CORRECT_OPTION',f'Вариант {option!r} предложен {n} раз и никогда не верен.',
                     'Ученик может исключать постоянный дистрактор автоматически.',
                     'Проверить баланс: убрать неуместный вариант или добавить реальный контрастный случай.',gid)
        if len(positions)>=6 and group.get('shuffleOptions') is False and len(set(positions))==1:
            note('WARNING','FIXED_ANSWER_POSITION',f'Правильная кнопка всегда стоит на позиции {positions[0]}.',
                 'Порядок явно фиксирован и позволяет угадывать.',
                 'Проверить обоснование фиксированного порядка или включить перемешивание.',gid)
        phrases=defaultdict(list)
        near=defaultdict(list)
        contexts=defaultdict(list)
        for i,q in enumerate(qs,1):
            exp=q.get('explain','').strip()
            if exp:phrases[_norm(exp)].append(i)
            prompt=_norm(q.get('prompt',''))
            if prompt:near[prompt].append(i)
            context=q.get('context','')
            if context and q.get('answers'):
                contexts[_norm(context)].append((i,q['answers'][0]))
            hints=[('answerHint',q.get('answerHint','')),('translation',q.get('translation',''))]
            # inputFormat describes controls (e.g. how to click «Без артикля»), not this question's answer.
            for src,hint in hints:
                for answer in q.get('answers',[]):
                    if len(_norm(answer))>=6 and _norm(answer) in _norm(hint) and re.search(r'\b'+re.escape(_norm(answer))+r'\b',_norm(hint)):
                        note('WARNING','DIRECT_ANSWER_HINT',f'{src} содержит ответ {answer!r}.',
                             'Ответ можно прочитать в подсказке без самостоятельной работы.',
                             'Заменить подсказку описанием ситуации; оставить полезное объяснение правила.',gid,i)
                        break
            if q.get('clues') and any(_norm(answer)==_norm(word) for answer in q.get('answers',[]) for word,*_ in q['clues']):
                note('WARNING','CLUE_IS_ANSWER','Подсказка clues содержит весь требуемый ответ.',
                     'Ученик может просто переписать ответ, не применяя грамматику.',
                     'Оставить основу или контекст, но убрать полную готовую форму.',gid,i)
            if q.get('tiles') and len(q['tiles'])<=len(q['answers'][0].split()) and len(q['tiles'])<=5:
                note('INFO','BUILD_WITHOUT_DISTRACTORS','Сборка фразы без лишних слов.',
                     'Иногда проверяет только порядок уже данных слов.',
                     'При необходимости добавить 1–2 правдоподобные лишние плитки.',gid,i)
            if len(_norm(exp))<18 or re.search(r'(?i)^(повтори(те)? правило|посмотри правило|подумай ещё|вспомни правило)[.! ]*$',exp):
                note('WARNING','GENERIC_EXPLANATION','Объяснение очень короткое или шаблонное.',
                     'После потери последней жизни нужен разбор конкретной ошибки.',
                     'Назвать проверяемую конструкцию, условие её применения и контраст.',gid,i)
            if q.get('options'):
                for o in q['options']:
                    if re.search(r'(?i)\b(relojs|hotels|reys|profesors)\b',o):
                        note('WARNING','SUSPICIOUS_DISTRACTOR',f'Вариант {o!r} выглядит искусственным.',
                             'Обнаружен известный по аудиту пример неестественной формы; автоматическая оценка не является словарём.',
                             'Проверить форму по RAE/ASALE и заменить на распространённую ошибку, если неуместна.',gid,i)
            # Deliberately restricted: prompts in 5.2 make grammar decision from Russian meta-comment.
            if (re.search(r'(?i)(без артикл|не нужен артикл|выбери (?:определ[её]нный|неопредел[её]нный) артикл)',context)
                    or (re.search(r'(?i)(сообщи национальност|просто назови професси)',context) and
                        any(a in ('Без артикля','без артикля') for a in q.get('answers',[])))):
                note('WARNING','CONTEXT_LEAK',f'Русский контекст может подсказать грамматическую категорию.',
                     'Ученик может решить вопрос по подсказке, не анализируя испанскую фразу.',
                     'Переформулировать как коммуникативную ситуацию, сохранив цель проверки.',gid,i)
            prompt_action=(q.get('inputFormat') or {}).get('instruction','') or group.get('instruction','')
            if q.get('options') and re.search(r'(?i)\b(впиши|напиши|введите)\b',prompt_action) and not any(_mode(z)=='input' for z in qs):
                note('INFO','INPUT_WORDING_FOR_CHOICES','Инструкция предлагает ввод, хотя это вопрос с выбором.',
                     'Тип действия и формулировка могут противоречить друг другу.',
                     'Использовать «выбери» или добавить поле ввода, если это учебная цель.',gid,i)
            if unit.get('number',999)<=10 and re.search(r'\b(?:he|has|han)\s+\w+(?:ado|ido)\b',q.get('prompt',''),re.I):
                note('INFO','POSSIBLE_UNTAUGHT_GRAMMAR','Ранняя тема содержит возможную конструкцию perfecto.',
                     'Встречается форма, которая может ещё не быть изучена; эвристика не доказывает нарушение.',
                     'Ручная сверка с картой теории и известными предпосылками.',gid,i)
        for exp,ix in phrases.items():
            if len(ix)>=4:
                note('WARNING','REPEATED_EXPLANATION',f'Одно объяснение повторяется в {len(ix)} вопросах ({ix[:8]}).',
                     'Ответы и ошибки могут требовать разных уточнений.',
                     'Проверить отличия случаев и адресность каждого пояснения.',gid)
        for prompt,ix in near.items():
            if len(ix)>=3:
                note('WARNING','DUPLICATE_PROMPTS',f'Почти одинаковая формулировка встречается {len(ix)} раз ({ix[:8]}).',
                     'Повтор может не добавлять нового применения правила.',
                     'Проверить различия контекста и необходимость количества.',gid)
        for label,items in contexts.items():
            if len(items)>=3 and len({answer for _,answer in items})==1 and len(label)>14:
                note('WARNING','CONTEXT_PREDICTS_ANSWER',f'Одинаковая подпись в {len(items)} вопросах всегда ведёт к {items[0][1]!r}.',
                     'Можно выучить ответ по подписи; это статистический сигнал, не доказательство.',
                     'Сопоставить с другими вопросами, проверить полезность подписи.',gid)
    if len(exercise_modes)>=8 and len(set(exercise_modes))==1:
        note('INFO','UNIT_FORMAT_DIVERSITY','Все упражнения юнита используют один тип ответа.',
             'Одно действие может не проверить перенос навыка в новый контекст.',
             'При следующей переработке подумать о распознавании, вводе, исправлении или диалоге.')
    return out


def summarize(findings: Iterable[Finding]) -> dict:
    data=list(findings)
    return {'totals':{s:sum(f.severity==s for f in data) for s in SEVERITIES},
            'byRule':dict(sorted(Counter(f.rule for f in data).items(),key=lambda x:(-x[1],x[0]))),
            'byUnit':{str(u):dict(Counter(f.severity for f in data if f.unit==u)) for u in sorted({f.unit for f in data if f.unit is not None})},
            'baselineErrors':sum(f.severity=='ERROR' and f.baseline for f in data),
            'newErrors':len(breaking_findings(data))}


def markdown_report(findings: list[Finding], checked_units: int, checked_questions: int) -> str:
    stats=summarize(findings)
    lines=['# Аудит JSON и педагогического качества грамматики','',
           f'Проверено **{checked_units} юнитов**, **{checked_questions} вопросов** (включая мини-проверки).',
           '',f"**ERROR: {stats['totals']['ERROR']} · WARNING: {stats['totals']['WARNING']} · INFO: {stats['totals']['INFO']}**",
           f"Известных ранее ошибок структуры с документированным исключением: {stats['baselineErrors']}; новых блокирующих: {stats['newErrors']}.",
           '', '## Частые сигналы', '', '| Правило | Количество |', '|---|---:|']
    lines += [f'| {r} | {n} |' for r,n in list(stats['byRule'].items())[:25]]
    units=sorted(((int(k),v) for k,v in stats['byUnit'].items()),key=lambda p:(-p[1].get('ERROR',0),-p[1].get('WARNING',0),-p[1].get('INFO',0)))
    lines+=['','## Приоритетные юниты', '', '| Юнит | ERROR | WARNING | INFO |', '|---:|---:|---:|---:|']
    lines += [f"| {u} | {v.get('ERROR',0)} | {v.get('WARNING',0)} | {v.get('INFO',0)} |" for u,v in units[:20]]
    lines+=['','## Десять примеров для методической проверки', '',
            'Это **не автоматически доказанные грамматические ошибки**. Каждый пункт требует проверки преподавателем.','']
    priority=['CONTEXT_LEAK','NEVER_CORRECT_OPTION','DIRECT_ANSWER_HINT','SUSPICIOUS_DISTRACTOR','REPEATED_EXPLANATION','DOMINANT_ANSWER','LONG_HOMOGENEOUS','GENERIC_EXPLANATION']
    candidates=sorted((f for f in findings if f.severity=='WARNING'),key=lambda f:(priority.index(f.rule) if f.rule in priority else 100,f.unit or 999,f.group or '',f.question or 0))
    sample=[]; used=set(); per_rule=Counter()
    for f in candidates:
        key=(f.rule,f.unit,f.group)
        if key in used or per_rule[f.rule]>=2:continue
        sample.append(f);used.add(key);per_rule[f.rule]+=1
        if len(sample)==10:break
    for f in sample:
        loc=f'{f.unit}' + (f' · {f.group}' if f.group else '') + (f' · вопрос {f.question}' if f.question else '')
        lines.extend([f'- **{loc} · {f.rule}:** {f.message} Причина: {f.reason} Рекомендация: {f.recommendation}'])
    lines+=['','## Граница автоматизации','',
            'WARNING и INFO не блокируют CI. Схема не проверяет смысл русского перевода, нормативность испанской формы или соответствие теории в полном объёме.',
            'Ручная сверка каждого юнита с учебником, RAE/ASALE и предшествующими темами обязательна.',
            'В машинном JSON-отчёте каждая находка содержит номер юнита, упражнение, вопрос, правило, причину и рекомендуемое действие.', '']
    return '\n'.join(lines)


def count_content(directory: Path = DIRECTORY, only: set[int] | None = None) -> tuple[int,int]:
    count=questions=0
    for p in directory.glob('[0-9]*.json'):
        try:
            u=json.loads(p.read_text(encoding='utf-8'))
        except (ValueError,UnicodeError):
            # inspect_directory reports JSON_PARSE; statistics must not crash.
            continue
        if not isinstance(u,dict):
            continue
        if only and u.get('number') not in only:continue
        count+=1
        questions+=sum(len(g['questions']) for g in u.get('exercises',[]))
        questions+=sum(len(s['check']['questions']) for s in u.get('sections',[]) if s.get('check'))
    return count,questions
