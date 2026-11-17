import http from 'node:http';
import fs from 'node:fs/promises';
import {watch} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn,execFile} from 'node:child_process';

const directory=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(directory,'..');
const python=process.env.PYTHON_BIN||(process.platform==='win32'?'py':'python3');
const pythonArgs=python==='py'?['-3']:[];
let child,backendPort,closing=false,restarting=false,reloadTimer;
const watchers=[];

function startBackend(){
  backendPort=undefined;
  return new Promise((resolve,reject)=>{
    let output='',settled=false;
    const launched=spawn(python,[...pythonArgs,path.join(root,'backend','run.py'),'--port','0'],{cwd:root,windowsHide:true,stdio:['ignore','pipe','pipe']});
    child=launched;
    const timer=setTimeout(()=>fail(new Error('Python startup timed out. Set PYTHON_BIN to a working Python 3.10+ executable.')),15000);
    function fail(error){if(settled)return;settled=true;clearTimeout(timer);reject(error);}
    launched.stdout.on('data',chunk=>{
      output+=chunk;
      const match=output.match(/READY_PORT=(\d+)/);
      if(match&&!settled){settled=true;clearTimeout(timer);backendPort=Number(match[1]);resolve();}
    });
    launched.stderr.on('data',chunk=>process.stderr.write(chunk));
    launched.on('error',fail);
    launched.on('exit',code=>{
      if(!settled)fail(new Error('Python could not start. Check PYTHON_BIN and the backend error above.'));
      if(child===launched&&!closing&&!restarting){backendPort=undefined;console.error('Python backend exited:',code,'Save a backend file to retry, or restart the demo.');}
    });
  });
}

function stopBackend(){
  const owned=child;
  backendPort=undefined;
  if(!owned||owned.exitCode!==null)return Promise.resolve();
  return new Promise(resolve=>{
    if(process.platform==='win32'){
      // Only this server's owned Python launcher tree is stopped.
      execFile('taskkill',['/PID',String(owned.pid),'/T','/F'],{windowsHide:true},()=>resolve());
    }else{
      owned.once('exit',resolve);owned.kill('SIGTERM');setTimeout(resolve,1500).unref();
    }
  });
}

async function reloadBackend(){
  if(closing)return;
  if(restarting){reloadTimer=setTimeout(reloadBackend,300);return;}
  restarting=true;
  console.log('Backend files changed. Reloading Python…');
  try{await stopBackend();await startBackend();console.log('Backend reloaded. Refresh the browser for interface changes.');}
  catch(error){console.error(error.message);await stopBackend();}
  finally{restarting=false;}
}

function watchBackend(){
  const schedule=(event,filename)=>{
    if(filename&&/(__pycache__|\.pyc$)/.test(String(filename)))return;
    clearTimeout(reloadTimer);reloadTimer=setTimeout(reloadBackend,250);
  };
  for(const folder of ['app','data/sample']){
    try{watchers.push(watch(path.join(root,'backend',folder),{recursive:true},schedule));}
    catch{console.warn('Automatic backend reload unavailable. Restart the terminal after backend edits.');}
  }
  watchers.push(watch(path.join(root,'backend','run.py'),schedule));
}

const assets=new Set(['/','/index.html','/styles.css','/app.js']);
const types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8'};
function jsonError(res,status,message){if(!res.headersSent)res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify({error:message}));}
const server=http.createServer(async(req,res)=>{
  const pathname=new URL(req.url,'http://localhost').pathname;
  res.setHeader('X-Content-Type-Options','nosniff');
  if(pathname.startsWith('/api/')){
    if(!['GET','POST'].includes(req.method)){jsonError(res,405,'Method not allowed.');return;}
    if(!backendPort||restarting){jsonError(res,503,'The Python backend is restarting. Wait a moment, then retry. If it stays unavailable, check the demo terminal.');return;}
    const chunks=[];let size=0;
    try{
      for await(const chunk of req){size+=chunk.length;if(size>16384){jsonError(res,413,'Request too large.');return;}chunks.push(chunk);}
      const upstream=http.request({hostname:'127.0.0.1',port:backendPort,path:pathname,method:req.method,headers:{'Content-Type':'application/json','Content-Length':size}},response=>{
        res.writeHead(response.statusCode,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});response.pipe(res);
      });
      upstream.setTimeout(10000,()=>upstream.destroy(new Error('Backend timeout')));
      upstream.on('error',()=>jsonError(res,502,'The Python backend is unavailable. Wait for reload, or restart the demo terminal.'));
      req.on('aborted',()=>upstream.destroy());upstream.end(Buffer.concat(chunks));
    }catch{if(!res.writableEnded)jsonError(res,400,'Unable to read the request.');}
    return;
  }
  if(!assets.has(pathname)||req.method!=='GET'){res.writeHead(404);res.end('Not found');return;}
  try{
    const file=path.join(directory,'public',pathname==='/'?'index.html':pathname.slice(1));
    const body=await fs.readFile(file);
    res.writeHead(200,{'Content-Type':types[path.extname(file)],'Cache-Control':'no-store'});res.end(body);
  }catch{res.writeHead(404);res.end('Not found');}
});

async function shutdown(code=0){
  if(closing)return;closing=true;clearTimeout(reloadTimer);watchers.forEach(watcher=>watcher.close());
  await stopBackend();server.close(()=>process.exit(code));setTimeout(()=>process.exit(code),1500).unref();
}
process.on('SIGINT',()=>shutdown());process.on('SIGTERM',()=>shutdown());
server.on('error',error=>{console.error(error.message);shutdown(1);});
try{
  await startBackend();watchBackend();
  server.listen(Number(process.env.PORT||3000),'127.0.0.1',()=>console.log(`Demo ready: http://127.0.0.1:${server.address().port} (Python auto-reload enabled)`));
}catch(error){console.error(error.message);await shutdown(1);}
