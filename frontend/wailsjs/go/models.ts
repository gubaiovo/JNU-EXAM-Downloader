export namespace main {
	
	export class NoticeInfo {
	    show: boolean;
	    id: string;
	    title: string;
	    content: string;
	
	    static createFrom(source: any = {}) {
	        return new NoticeInfo(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.show = source["show"];
	        this.id = source["id"];
	        this.title = source["title"];
	        this.content = source["content"];
	    }
	}
	export class CheckResult {
	    has_update: boolean;
	    current_ver: string;
	    remote_ver: string;
	    update_desc: string;
	    is_force: boolean;
	    download_url: string;
	    checksum: string;
	    notice: NoticeInfo;
	
	    static createFrom(source: any = {}) {
	        return new CheckResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.has_update = source["has_update"];
	        this.current_ver = source["current_ver"];
	        this.remote_ver = source["remote_ver"];
	        this.update_desc = source["update_desc"];
	        this.is_force = source["is_force"];
	        this.download_url = source["download_url"];
	        this.checksum = source["checksum"];
	        this.notice = this.convertValues(source["notice"], NoticeInfo);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class FileNode {
	    name: string;
	    path: string;
	    size: any;
	    files?: FileNode[];
	    dirs?: FileNode[];
	    cf_url?: string;
	    github_raw_url?: string;
	
	    static createFrom(source: any = {}) {
	        return new FileNode(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.path = source["path"];
	        this.size = source["size"];
	        this.files = this.convertValues(source["files"], FileNode);
	        this.dirs = this.convertValues(source["dirs"], FileNode);
	        this.cf_url = source["cf_url"];
	        this.github_raw_url = source["github_raw_url"];
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}

}

