import {getAuth, signInWithEmailAndPassword} from "https://www.gstatic.com/firebasejs/9.9.0/firebase-auth.js";

import {load_queue} from "./io.js";
import {Datastore} from "./datastore.js";
import {Screen} from "./screen.js"

class Manager {

    constructor() {
        this.main = document.getElementById("main");

    }

    async load() {
        this.set_screen_text('Loading...')
        this.datastore = new Datastore()
        await this.datastore.load()
    }

    async login(email, passcode, queue_id) {
        this.set_screen_text('Logging in...')
        const auth = getAuth();
        signInWithEmailAndPassword(auth, email, passcode)
            .then(async (userCredential) => {
                console.log('Successful login')
                // Signed in
                await this.load()
                this.user_id = userCredential.user.uid
                this.queue_name = queue_id

                if (!(this.queue_name in this.datastore.lemma_queues)) {
                    this.set_screen_text('Invalid queue ID. Refresh to retry.')
                }

                this.queue = this.datastore.lemma_queues[this.queue_name]
                this.update_queue_and_render()
            })
            .catch((error) => {
                console.error(error)
                this.set_screen_text('Failed login. Refresh to retry.')
            });
    }

    async login_screen(){

        const element = document.getElementById("main");

        let that = this

        let form = document.createElement("form");
        form.id = "form"

        // User ID
        form.innerHTML += 'Email: '
        let name = document.createElement('input')
        name.id = 'user_id'
        name.name = 'user_id'
        name.type = 'text'
        form.appendChild(name)

        // User ID
        form.innerHTML += '<br>Passcode: '
        let passcode = document.createElement('input')
        passcode.id = 'passcode'
        passcode.name = 'passcode'
        passcode.type = 'password'
        form.appendChild(passcode)

        // Queue
        form.innerHTML += '<br>Queue ID: '
        let queue = document.createElement('input')
        queue.id = 'queue_id'
        queue.name = 'queue_id'
        queue.type = 'text'
        form.appendChild(queue)
        form.innerHTML += '<br>'

        // Submit
        let submit = document.createElement("input");
        submit.type = "submit"
        form.appendChild(submit)
        form.innerHTML += '<br>'

        // Warning cell
        let warnings = document.createElement('p')
        warnings.style.color = 'red'
        warnings.id = 'warnings'
        form.appendChild(warnings)
        form.onsubmit = function() { return that.submit_credentials() }

        element.innerHTML = ''
        element.appendChild(form)
    }

    submit_credentials() {
        // Sanity check
        const user_id = document.getElementById(`user_id`).value
        const passcode = document.getElementById(`passcode`).value
        const queue_name = document.getElementById(`queue_id`).value

        this.login(user_id, passcode, queue_name)
        return false
    }

    set_screen_text(process_text) {
        this.main.innerHTML = process_text
    }

    update_queue_and_render() {
        this.set_screen_text('Loading queue...')
        load_queue(this.user_id, this.queue_name).then((snapshot) => {
            let found = false
            if (snapshot.exists()) {
                // Find queue index by going through until one isn't done
                let user_data = snapshot.val()
                for (let i = 0; i < this.queue.length; i++) {
                    let lemma_i = this.queue[i]
                    if (!(lemma_i in user_data)) {
                        this.queue_index = i
                        found = true
                        break
                    }
                }
            } else {
                // Nothing saved
                found = true
                this.queue_index = 0
            }
            if (found) {
                this.update_feature_list().then(() => {
                    this.render()
                })
            } else {
                this.set_screen_text('Thank you for participating.')
            }
        })
    }

    async update_feature_list() {
        this.set_screen_text('Refreshing feature list...')
        await this.datastore.refresh_feature_list(this.user_id)
    }

    render() {
        this.set_screen_text('Rendering...')
        const lemma = this.queue[this.queue_index]
        new Screen(lemma, this)
    }

}

function start() {
    let rend = new Manager();
    rend.login_screen()
}

window.start = start;
