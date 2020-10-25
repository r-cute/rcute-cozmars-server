class StopIteration{}
class RPCError extends Error{
    constructor(message) {
        super(message);
        this.name = 'RPCError';
    }
}

class Queue {
    constructor(size) {
        this.size = size;
        this._resolve = null;
        this._reject = null;
        this._q = [];
    }

    get full() {
        return this.size>0 && this.size<=this._q.length;
    }

    put_nowait(v, force=false) {
        if(this.full && !force) return;
        if(this._resolve) {
            this._resolve(v);
            this._resolve = null;
        } else {
            this._q.push(v);
        }
    }

    get() {
        return new Promise((resolve, reject)=>{
            this._q.length?resolve(this._q.shift()):this._resolve=resolve;
        });
    }

    [Symbol.asyncIterator]() {
        return this;
    }

    close() {
        this.put_nowait(new StopIteration(), true)
    }

    next() {
        return this.get().then(v=>{            
            if(v instanceof Error) throw v;            
            return (v instanceof StopIteration)?{done:true}:{done:false, value:v}
        })
    }
}

class RPCFuture extends Promise {
    constructor(cb, msgid, client, q_size=0) {
        super(cb);
        this._client = client;
        this._msgid = msgid;
        this._cancelled = false;
        this._q_size = q_size;
        this._response_stream = null;
        this._rj = null;
    }

    get resolve() {
        return this._rj.resolve;
    }

    get reject() {
        return this._rj.reject;
    }

    get cancelled() {
        return this._cancelled;
    }

    get response_stream() {
        if(!this._response_stream)
            this._response_stream = new Queue(this._q_size);
        return this._response_stream;
    }

    cancel() {
        if(!this._cancelled){
            this._client._cancel(this._msgid);
            this._cancelled = true;
        }
    }

    [Symbol.asyncIterator]() {
        return this.response_stream;
    }
}

class RPCClient{
    static REQUEST = 0
    static RESPONSE = 1
    static NOTIFY = 2
    static REQUEST_STREAM_CHUNCK = 3
    static RESPONSE_STREAM_CHUNCK = 4
    static REQUEST_STREAM_END = 5
    static RESPONSE_STREAM_END = 6
    static REQUEST_CANCEL = 7
    static RESPONSE_CANCEL = 8

    constructor(ws) {
        this._ws = ws;        
        this._mid = 0;
        this._promises = {};
        const that = this;
        ws.onmessage = async function(data) {
        	try{
	            const msg = msgpack.deserialize(await data.data.arrayBuffer());
	            const [msgtype, msgid] = msg.slice(0, 2);
	            const p = that._promises[msgid.toString()];
	            if (p)
	                switch(msgtype) {
	                    case RPCClient.RESPONSE:
	                        const [err, result] = msg.slice(2);
	                        if(err){
	                            if(!p.cancelled) {
	                                const e = new RPCError(err);
	                                p.reject(e);
	                                p._response_stream && p._response_stream.put_nowait(e, true);
	                            }
	                        }else{
	                            p.resolve(result);
	                        }
	                        that._pop_promise(msgid);
	                        break;

	                    case RPCClient.RESPONSE_STREAM_CHUNCK:
	                        p.response_stream.put_nowait(msg[2], true);
	                        break;

	                    case RPCClient.RESPONSE_STREAM_END:
	                        p.response_stream.put_nowait(new StopIteration(), true);
	                        p.resolve();
	                        that._pop_promise(msgid);
	                        break;                        
	                }
	         } catch (e) {
	         	console.error(e)
	         }            
        }
    }

    rpc(method, params, request_stream=null) {
        const msgid = this._next_msgid();
        const rj={}
        const p = new RPCFuture((resolve, reject)=>{
            rj.resolve=resolve;
            rj.reject=reject;
            this._send_request(msgid, method, params);
            if (request_stream){
                if(typeof request_stream[Symbol.iterator] === 'function'){
                    for(var e of request_stream)
                        this._send_stream_chunck(msgid, e)
                    this._send_stream_end(msgid)
                }else if(typeof request_stream[Symbol.asyncIterator] === 'function'){
                    const that = this;
                    (async function(){
                        for await(var e of request_stream)
                            that._send_stream_chunck(msgid, e)
                        that._send_stream_end(msgid)
                    })()
                }
            }
        }, msgid, this);
        p._rj = rj;
        this._promises[msgid] = p;
        return p;
    }

    _cancel(msgid) {
        const p = this._pop_promise(msgid);
        if(p) {
            const e = new RPCError('Cancelled by client');
            p.resolve();//p.reject(e);
            p._response_stream && p._response_stream.put_nowait(e, true);
        }
        this._send_cancel(msgid)
    }

    _send_cancel(msgid) {
        this._ws.send(msgpack.serialize([RPCClient.REQUEST_CANCEL, msgid]))
    }

    _send_stream_chunck(msgid, chunck) {
        this._ws.send(msgpack.serialize([RPCClient.REQUEST_STREAM_CHUNCK, msgid, chunck]))
    }

    _send_stream_end(msgid) {
        this._ws.send(msgpack.serialize([RPCClient.REQUEST_STREAM_END, msgid]))
    }

    _send_request(msgid, method, params) {
        this._ws.send(msgpack.serialize([RPCClient.REQUEST, msgid, method, params]))
    }

    _pop_promise(msgid) {
        const p = this._promises[msgid.toString()];
        delete this._promises[msgid.toString()];
        return p;
    }

    _next_msgid() {
        if(this._mid > 2**20)
            this._mid = 0;
        this._mid += 1;
        return this._mid;
    }

}
