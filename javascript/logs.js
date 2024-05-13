export class Logs {

    constructor() {
        this.logs = {}
        this.log_index = 0
    }

    log(action, argument_1, argument_2) {
        const log_obj = {'time': this.get_time(),
            'action': action,
            'arg_1': argument_1,
            'arg_2': argument_2}
        console.log(log_obj)
        this.logs[this.log_index] = log_obj
        this.log_index += 1
    }

    get_time() {
        return new Date().toString();
    }

    get_data() {
        console.log(this.logs)
        return this.logs
    }
}