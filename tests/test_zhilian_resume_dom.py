"""Execute the real adapter script against a DOM with the live chooser classes."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from bosshunter.executor.platform_delivery import _script


@pytest.mark.parametrize('scenario', ['match', 'missing', 'duplicate', 'wrong_job', 'transparent'])
def test_resume_dom_selects_exact_pdf_and_submits_only_prepared_choice(scenario):
    node = shutil.which('node')
    module = Path(__file__).resolve().parents[1] / 'src/bosshunter/web/frontend/node_modules/jsdom'
    if not node or not module.exists():
        pytest.skip('Existing frontend jsdom and Node required')
    job = {'source_platform': 'zhilian', 'source_job_id': 'CC123', 'url': 'https://www.zhaopin.com/jobdetail/CC123.htm', 'title': '工程师', 'company': '示例公司'}
    scripts = {a: _script(job, resume_name='approved-resume.pdf', resume_action=a) for a in ['prepare', 'inspect', 'submit']}
    harness = r'''
const {JSDOM}=require(MODULE);
const scenario=SCENARIO, scripts=SCRIPTS;
const title=scenario==='wrong_job'?'其他岗位':'工程师';
const file=scenario==='missing'?'other.pdf':'approved-resume.pdf';
const item=`<div class="a-attachment-select__item--attachment"><p class="attachment-name">${file}</p></div>`;
const dom=new JSDOM(`<body><div class="summary-planes__content"><h1 class="summary-planes__title">${title}</h1><button>立即投递</button></div><a class="company-info__name">示例公司</a><div class="a-modal a-job-apply-workflow--attachment-select" style="opacity:${scenario==='transparent'?0:1}"><p>请选择要投递的简历</p>${item}${scenario==='duplicate'?item:''}<p class="a-attachment-select__action-btn__default"><span class="radio-icon radio-unchecked"></span>每次投递默认发送该简历</p><a class="a-attachment-select__action-btn__delivery">投递简历</a></div></body>`,{url:'https://www.zhaopin.com/jobdetail/CC123.htm'});
const win=dom.window;
global.document=win.document; global.location=win.location;
global.innerWidth=1200;global.innerHeight=800;
Object.defineProperty(win.HTMLElement.prototype,'innerText',{get(){return this.textContent;}});
win.HTMLElement.prototype.getBoundingClientRect=()=>({width:100,height:30,left:10,top:10});
win.HTMLElement.prototype.scrollIntoView=()=>{};
global.getComputedStyle=el=>({display:el.style.display||'block',visibility:'visible',opacity:el.style.opacity||'1'});
const button=document.querySelector('.a-attachment-select__action-btn__delivery');
document.elementFromPoint=()=>button;
let chosen=0, submitted=0;
for(const el of document.querySelectorAll('.a-attachment-select__item--attachment')) el.addEventListener('click',()=>{chosen++;el.classList.add('is-active');});
document.querySelector('.a-attachment-select__action-btn__default').addEventListener('click',()=>{const icon=document.querySelector('.radio-icon');icon.className='radio-icon radio';});
button.addEventListener('click',e=>{e.preventDefault();submitted++;});
const prepare=JSON.parse(eval(scripts.prepare));
const inspect=JSON.parse(eval(scripts.inspect));
const submit=JSON.parse(eval(scripts.submit));
console.log(JSON.stringify({prepare,inspect,submit,chosen,submitted}));
'''.replace('MODULE', json.dumps(str(module))).replace('SCENARIO', json.dumps(scenario)).replace('SCRIPTS', json.dumps(scripts))
    data = json.loads(subprocess.run([node, '-e', harness], check=True, capture_output=True, text=True).stdout)
    if scenario == 'match':
        assert data['prepare']['state'] == 'resume_preparing'
        assert data['inspect']['state'] == 'resume_ready'
        assert data['submit']['state'] == 'resume_submitted'
        assert data['chosen'] == 1 and data['submitted'] == 1
    else:
        assert data['chosen'] == 0 and data['submitted'] == 0
