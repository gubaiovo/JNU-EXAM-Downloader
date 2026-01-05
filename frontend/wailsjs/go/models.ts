export namespace main {
	
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

