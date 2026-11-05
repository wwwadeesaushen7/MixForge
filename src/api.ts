export async function api<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch('/api'+path,body===undefined?undefined:{method:'POST',headers:body instanceof FormData?undefined:{'Content-Type':'application/json'},body:body instanceof FormData?body:JSON.stringify(body)});
 if(!response.ok){let detail='The audio engine could not complete this request.';try{const e=await response.json();detail=typeof e.detail==='string'?e.detail:JSON.stringify(e.detail)}catch{}throw Error(detail)}
 return response.json();
}
export async function job<T>(id:string,onProgress:(n:number,m:string)=>void):Promise<T>{
 for(;;){const j=await api<{status:string;progress:number;message:string;result:T}>('/jobs/'+id);onProgress(j.progress,j.message);if(j.status==='done')return j.result;if(j.status==='error')throw Error(j.message);await new Promise(r=>setTimeout(r,550))}
}
