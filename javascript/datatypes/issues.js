export class Issues {
    constructor() {
        this.failed = false
        this.issues = []
    }

    is_failed() {
        return this.failed
    }

    add_issue(issue_text) {
        this.failed = true
        this.issues.push(issue_text)
    }

    get_issues() {
        return this.issues
    }

    merge_issues(issues) {
        for (const issue of issues.get_issues()) {
            this.add_issue(issue)
        }
    }
}