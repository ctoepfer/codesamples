export namespace gui {
	
	export class ConfigResult {
	    ok: boolean;
	    path: string;
	    appName: string;
	    developerModeIntro: string;
	    developerModeImage: string;
	    manualIpHelp: string;
	    installButtonLabel: string;
	    postInstallMessage: string;
	    error?: string;
	
	    static createFrom(source: any = {}) {
	        return new ConfigResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.ok = source["ok"];
	        this.path = source["path"];
	        this.appName = source["appName"];
	        this.developerModeIntro = source["developerModeIntro"];
	        this.developerModeImage = source["developerModeImage"];
	        this.manualIpHelp = source["manualIpHelp"];
	        this.installButtonLabel = source["installButtonLabel"];
	        this.postInstallMessage = source["postInstallMessage"];
	        this.error = source["error"];
	    }
	}
	export class DeviceResult {
	    ip: string;
	    name: string;
	
	    static createFrom(source: any = {}) {
	        return new DeviceResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.ip = source["ip"];
	        this.name = source["name"];
	    }
	}
	export class InstallResult {
	    ok: boolean;
	    version?: string;
	    error?: string;
	
	    static createFrom(source: any = {}) {
	        return new InstallResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.ok = source["ok"];
	        this.version = source["version"];
	        this.error = source["error"];
	    }
	}

}

