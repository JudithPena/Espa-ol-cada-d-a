// Stage-3 regression: exercise actual production grading functions in the site bundle.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const template = fs.readFileSync('espanol/site_template.html','utf8');
const bundle = template.match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace('/*__GRAMMAR_PLAYER__*/',fs.readFileSync('espanol/grammar_player.js','utf8'));
const catalog = JSON.parse(fs.readFileSync('content/grammar/accent_policies.json','utf8'));
function runtime() {
  const noop = ()=>{};
  const ctx = vm.createContext({console,setTimeout:noop,clearTimeout:noop,addEventListener:noop,
    localStorage:{getItem:()=>null,setItem:noop,removeItem:noop},
    window:{addEventListener:noop},
    document:{documentElement:{classList:{toggle:noop}},addEventListener:noop,
      getElementById:()=>null,querySelector:()=>({focus:noop})},
    matchMedia:()=>({matches:false,addEventListener:noop}),navigator:{},
    speechSynthesis:{getVoices:()=>[],addEventListener:noop}
  });
  const data={lessons:[],units:[],intervals:[1],grammar:[]};
  vm.runInContext(bundle.replace('/*__DATA__*/{}',JSON.stringify(data))
    .replace(/render\(\);\s*$/,''),ctx);
  return expression=>vm.runInContext(expression,ctx);
}
const run=runtime();
const grade=(question,value,group={})=>
  JSON.parse(run('JSON.stringify(grammarResult('+JSON.stringify(question)+','+
    JSON.stringify(value)+','+JSON.stringify(group)+',true))'));
const meta=(answer,policy='soft')=>({prompt:'Впиши ответ',answers:[answer],explain:'Грамматическое правило',accentPolicy:policy});

test('acute vowels, Unicode composition, case and all alternatives have stable green/yellow results',()=>{
  for(const [correct,typed] of [['café','cafe'],['teléfono','telefono'],['rubíes','rubies'],['canción','cancion']]){
    const q=meta(correct);
    assert.equal(grade(q,correct.toUpperCase()).status,'correct');
    assert.equal(grade(q,typed).status,'almost');
    assert.equal(grade(q,typed).good,true);
    assert.equal(grade({...q,accentPolicy:'strict'},typed).status,'wrong');
  }
  assert.equal(grade(meta('café'),'cafe\u0301').status,'correct');
  const q={prompt:'Forma plural',answers:['rubíes','rubís'],explain:'Обе формы допустимы.',accentPolicy:'soft'};
  for(const value of q.answers)assert.equal(grade(q,value).status,'correct');
  assert.equal(grade(q,'rubis').status,'almost');
  assert.equal(grade(q,'rubios').status,'wrong');
});
test('meaning-changing accents never become yellow, even with soft policy',()=>{
  for(const [expected,without] of [
    ['habló','hablo'],['tú','tu'],['él','el'],['está','esta'],['sí','si'],
    ['más','mas'],['mí','mi'],['dónde','donde']]){
    const q=meta(expected,'soft'),answer=grade(q,without);
    assert.equal(answer.status,'wrong',expected+'/'+without);
    assert.equal(answer.good,false,expected+'/'+without);
    assert.ok(answer.explanation,expected+' must explain the actual contrast');
  }
});
test('ñ and ü are letters, never forgiven by accent normalization',()=>{
  for(const [expected,without] of [['año','ano'],['niño','nino'],['pingüino','pinguino']]){
    const q=meta(expected);
    assert.equal(grade(q,without).status,'wrong');
    assert.equal(grade(q,expected).status,'correct');
  }
  assert.equal(grade(meta('mañana'),'manana').status,'wrong');
});
test('explicit contextual contrasts and fail-closed policy',()=>{
  const q={...meta('más cómodo','contextual'),
    accentContrasts:[{expected:'más',entered:'mas',explanation:'mas is a conjunction'}]};
  const wrong=grade(q,'mas cómodo');
  assert.equal(wrong.status,'wrong');
  assert.match(wrong.explanation,/conjunction/);
  assert.equal(grade(q,'más comodo').status,'almost');
  assert.equal(grade({...q,accentContrasts:[]},'más comodo').status,'wrong');
  const soft=meta('estáis','soft');
  assert.equal(grade(soft,'estais').status,'almost');
  assert.equal(grade({...soft,accentPolicy:'strict'},'estais').status,'wrong');
});
test('only written framing punctuation is ignored when explicitly enabled',()=>{
  const q={...meta('¿Tenéis frío?'),normalize:'phrase',
    accentPolicy:'contextual',
    accentContrasts:[{expected:'tenéis',entered:'teneis',explanation:'Verb needs stress'}]};
  for(const answer of ['¿Tenéis frío?','Tenéis frío','Tenéis frío.','TENÉIS FRÍO!']){
    assert.equal(grade(q,answer).status,'correct',answer);
  }
  assert.equal(grade(q,'Teneis frío').status,'wrong');
  assert.equal(grade({...q,normalize:undefined},'Tenéis frío').status,'wrong');
});
test('real contextual policy catalog points to matching intact lesson positions',()=>{
  for(const [unitId,groups] of Object.entries(catalog)){
    const prefix=unitId.split('_')[0];
    const name=fs.readdirSync('content/grammar').find(f=>f.startsWith(prefix+'_')&&f.endsWith('.json'));
    assert.ok(name,'missing unit '+unitId);
    const u=JSON.parse(fs.readFileSync('content/grammar/'+name,'utf8'));
    assert.equal(u.id,unitId);
    const all=[...u.sections.map(s=>s.check),...u.exercises];
    for(const [groupId,questions] of Object.entries(groups)){
      const group=all.find(g=>g.id===groupId);assert.ok(group,groupId);
      for(const [index,policy] of Object.entries(questions)){
        const q=group.questions[Number(index)];assert.ok(q);
        assert.equal(q.answers[0],policy.answer);
        const target={...q,accentPolicy:policy.accentPolicy,accentContrasts:policy.accentContrasts};
        assert.equal(grade(target,q.answers[0],group).good,true);
        for(const pair of policy.accentContrasts){
          const typed=q.answers[0].replace(new RegExp(pair.expected,'iu'),pair.entered);
          if(typed!==q.answers[0]){
            const result=grade(target,typed,group);
            assert.equal(result.status,'wrong',unitId+'/'+groupId+'/'+index);
            assert.ok(result.explanation);
          }
        }
      }
    }
  }
});
test('mixed multi-gap submission marks only truly wrong gap and accepts accent-only gap',()=>{
  const q={prompt:'¿___ ___?',answers:['estás aquí'],explain:'Correcta forma',
    gapParts:['¿',' ','?'],gapWordCounts:[1,1],accentPolicy:'contextual',
    accentContrasts:[{expected:'estás',entered:'estas',explanation:'Different verb form'}]};
  const r=run('JSON.stringify(gGapMistakes('+JSON.stringify(q)+
    ',{gapValues:["estas","aqui"],value:"estas aqui"},{}))');
  const result=JSON.parse(r);
  assert.deepEqual(result.wrong,[true,false]);
  assert.deepEqual(result.almost,[false,true]);
  const feedback=run('gMistakeAnalysis('+JSON.stringify(q)+
    ',{value:"estas aqui",gapValues:["estas","aqui"]},{})');
  assert.match(feedback,/Пропуск 1/);
  assert.match(feedback,/Пропуск 2/);
  assert.match(feedback,/Верный ответ/);
});
test('warning variants remain accepted, and errors receive tailored feedback',()=>{
  const q={...meta('el libro'),answers:['el libro','un libro'],
    answerWarnings:{'un libro':{preferred:'el libro',message:'Допустимый вариант',
      explanation:'Both forms permitted',source:'https://dle.rae.es/'} }};
  assert.equal(grade(q,'un libro').status,'almost');
  assert.equal(grade(q,'un libro').reason,'variant');
  const wrong=grade(meta('habló'),'hablo');
  const message=run('grammarFeedbackExplanation('+JSON.stringify(meta('habló'))+
    ','+JSON.stringify(wrong)+')');
  assert.match(message,/прошедшее время/);
});

test('all real unit 34–45 alternatives are accepted without changing source answers',()=>{
  const filenames=fs.readdirSync('content/grammar').filter(name=>/^0(?:3[4-9]|4[0-5])_.*\.json$/.test(name));
  assert.equal(filenames.length,12);
  let answers=0,questions=0;
  for(const filename of filenames){
    const u=JSON.parse(fs.readFileSync('content/grammar/'+filename,'utf8'));
    for(const group of [...u.sections.map(s=>s.check),...u.exercises]){
      for(const q of group.questions){
        questions++;
        for(const accepted of q.answers){
          const r=grade(q,accepted,group);
          assert.equal(r.good,true,u.number+'/'+group.id+'/'+q.prompt+'/'+accepted);
          assert.ok(['correct','almost'].includes(r.status));
          answers++;
        }
        assert.equal(grade(q,'__nunca_es_una_respuesta_valida__',group).status,'wrong');
      }
    }
  }
  assert.ok(questions>350);
  assert.ok(answers>=questions);
});
