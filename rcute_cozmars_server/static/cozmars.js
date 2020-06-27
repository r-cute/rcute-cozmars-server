class rj {
	constructor(r, j) {
		this._r = r;
		this._j = j;
		this._resolved = this._rejected = false;
	}
	get resolve(){
		if (!this.done) this._resolved=true;
		return this._r
	}
	get reject(){
		if(!this.done) this._rejected=true;
		return this._j
	}
	get resolved(){return this._resolved}
	get rejected(){return this._rejected}
	get done(){return this._resolved || this.rejected}
}
class Cozmars {
	constructor(ip_or_serial) {
		this.host = ip_or_serial+(ip_or_serial.length==4?'.local':'');
		for (var a of ['infrared', 'button', 'sonar'])
			this[a] = {}
		this.infrared.state = [1, 1];
		this.camera = new Camera(this);
		this.lift = new Lift(this);
		this.head = new Head(this);
		this.buzzer = new Buzzer(this);
		this.motor = new Motor(this);
		this.screen = new Screen(this);
	}
	stopAllMotors() {
		if (this.connected) {
			this.motor.speed(0);
			this.head.angle(null);
			this.lift.height(null);
		}
	}
	connect(){
		const that = this;
		return new Promise((r,j)=>{
			const ws = new WebSocket('ws://'+that.host+'/rpc');
			this.ws = ws;
			ws.onopen = (e)=>{
				that._stub = new RPCClient(ws);
				that._startSensorTask();
				that._connected = true;
				r();
			}
			ws.onclose = (e)=>{console.debug('cozmars ws closed'); that.disconnect();} 
			ws.onerror = (e)=>{console.error('cozmars ws error:', e); j();}
		})
	}
	disconnect(){
		this._sensorTask && this._sensorTask.reject();
		this._senorRpc && this._senorRpc.cancel();			
		this.camera.close();
		this.ws.close();
		this._connected = false;
	}
	get connected() {
		return this._connected;
	}
	_startSensorTask() {
		return new Promise((r, j)=>{
			this._sensorTask = new rj(r, j);
			this._sensorRpc = this._stub.rpc('sensor_data', [3]);
			(async ()=>{
				for await(var [ev, data] of this._sensorRpc){
					try{
						switch(ev){
							case 'pressed':
							if (!data)
								this.button.held = this.button.doublePressed = false;
							this.button.pressed = data;
							this.button.released = !this.button.pressed
							break;
							case 'double_pressed': 
							this.button.pressed = this.button.doublePressed = data;
							this.button.released = !this.button.pressed
							break;
							case 'held':
							this.button.held = data;
							break;
							case 'sonar':
							this.sonar.distance = data;
							break;
							case 'lir':
							this.infrared.state = [data^1, this.infrared.state[1]];
							break;
							case 'rir':
							this.infrared.state = [this.infrared.state[0], data^1];
							break;
						}
					} catch (e) {
						console.error(e);
					}
				}
			})();
		});
	}
}
class Component {
	constructor(robot) {this._robot = robot}
	get _stub() {return this._robot._stub}
}
class Screen extends Component{
	get resolution() {
		return [240, 135]
	}
	async brightness(br, duration=null, fade_speed=null) {
		return await this._stub.rpc('backlight', br==undefined?[]:[br, duration, fade_speed])
	}
	async fill(bgr) {
		var [w, h] = this.resolution;
		await this._stub.rpc('fill', [this.bgr_to_color565(bgr), 0, 0, w, h]);
	}
	bgr_to_color565([b,g,r]) {
		return (r & 0xF8) << 8 | (g & 0xFC) << 3 | b >> 3
	}
}
class Lift extends Component{
	get max_height(){return 1}
	get min_height(){return 0}
	async height(height, duration=null, speed=null) {
		if (duration && speed)
			throw 'Cannot set both duration and speed';
		await this._stub.rpc('lift', height==undefined?[]:[height, duration, speed]);
	}
}
class Head extends Component{
	get max_angle(){return 30}
	get min_angle(){return -30}
	async angle(angle, duration=null, speed=null) {
		if (duration && speed)
			throw 'Cannot set both duration and speed';
		return await this._stub.rpc('head', angle==undefined?[]:[angle, duration, speed]);
	}
}
class Motor extends Component{
	async speed(sp, duration=null) {
		return await this._stub.rpc('speed', sp==undefined?[]:[sp, duration])
	}
}
class Camera extends Component{
	constructor(robot) {
		super(robot);
		this._resolution = [480, 360];
		this._framerate = 5;
	}
	get resolution(){return this._resolution }
	get framerate(){return this._framerate}
	set resolution(res){
		if (!this.closed)
			throw 'Cannot set resolution while camera is running';
		this._resolution = res;
	}
	set framerate(fr) {
		if (!this.closed)
			throw 'Cannot set resolution while camera is running';
		this._framerate = fr;
	}
	get closed() {return !this._task || this._task.done}
	getFrame() {
		this.open()
		return new Promise((r,j)=>{
			this._waitingList.push(new rj(r,j))
		})
	}
	close() {
		if (this.closed) return;
		this._task.resolve();
		this._rpc.cancel();
		var waiting;
		while(waiting=this._waitingList.pop())
			waiting.reject();
	}
	open() {		
		if (!this.closed) return;
		this._waitingList = [];
		new Promise((r,j)=>{
			this._task = new rj(r,j);
			const [w, h] = this.resolution;
			this._rpc = this._stub.rpc('camera', [w, h, this.framerate]);
			(async ()=>{
				for await(var f of this._rpc) {
					if (this._waitingList.length) {
						// f = this._decode(f);
						var waiting;
						while(waiting=this._waitingList.pop())
							waiting.resolve(f)
						this._lastRequest = Date.now();
					} else if (Date.now()-this._lastRequest > 3){
						this.close();
					}
				}
			})();
		});
	}
}
class Buzzer extends Component{
}
class Microphone extends Component{
}
