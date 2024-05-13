import {Lemma} from "./datatypes/lemma.js";
import {save_features, save_lemma, save_logs} from "./io.js";
import {make_empty_cell} from "./utilities.js";
import {Logs} from "./logs.js";

export class Screen {

    constructor(lemma_name, manager) {
        this.logs = new Logs()

        let that = this

        this.manager = manager

        console.log(`Initialising lemma ${lemma_name}`)
        this.lemma = new Lemma(lemma_name, this.manager.datastore, this)

        console.log(`Creating form and table title`)
        const element = document.getElementById("main");
        let form = document.createElement("form");
        form.autocomplete = 'off'
        form.id = "form"

        let table = document.createElement("table");
        table.id = 'table'
        table.style.borderCollapse = 'collapse'
        table.style.marginLeft = 'auto'
        table.style.marginRight = 'auto'
        form.appendChild(table)

        console.log(`Adding header`)
        let header = document.createElement('thead')
        // Adding word knowledge options
        let title_row = document.createElement("tr")
        let title_cell = document.createElement('td')
        //title_cell.style.fontSize = '150%'
        title_cell.style.padding = '15px'
        title_cell.colSpan= '6'
        title_cell.style.textAlign = 'center'

        let title = document.createElement("b")
        title.style.fontSize = '150%'
        title.innerHTML = this.lemma.word
        title_cell.appendChild(title)

        let pos = document.createElement("span")
        pos.style.fontSize = '150%'
        pos.innerHTML = ' (' + this.lemma.pos + ')'
        title_cell.appendChild(pos)

        let known = document.createElement('span')
        known.innerHTML = '<br>known? '
        known.style.fontSize = '80%'
        this.known_box = document.createElement('input')
        this.known_box.type = 'checkbox'
        this.known_box.checked = true
        known.appendChild(this.known_box)
        known.style.color = 'grey'

        this.known_box.onclick = function () {
            if (that.known_box.checked === false) {
                // If it has been set to false
                that.lemma.make_all_senses_unknown()
            }
        }

        title_cell.appendChild(known)

        title_row.appendChild(title_cell)

        header.appendChild(title_row)

        let header_row = document.createElement("tr")
        header_row.style.borderTop = '2px solid black'
        const headers = ['ID', 'Definition', 'Label', 'Connects&nbsp;To', 'Features', 'Tools'] // 'Image'
        for (const header of headers) {
            let cell = make_empty_cell()
            cell.innerHTML = '<b>' + header + '</b>'
            cell.style.textAlign = 'center'
            header_row.appendChild(cell)
        }
        header.appendChild(header_row)
        table.appendChild(header)

        let body = document.createElement('tbody')
        body.id = 'table_body'
        table.appendChild(body)

        console.log(`Adding footer`)
        let footer = document.createElement('tfoot')

        /* let word_knowledge_row = document.createElement("tr")
        footer.appendChild(word_knowledge_row)
        let word_knowledge_cell = document.createElement("td")
        word_knowledge_row.appendChild(word_knowledge_cell)
        word_knowledge_cell.colSpan = '6'
        word_knowledge_cell.style.textAlign = 'right'
        // word_knowledge_cell.style.color = 'red'
        word_knowledge_row.style.borderTop = '2px solid black'

        this.word_knowledge = null
        let index = 0
        const options = ['I feel comfortable using this word', 'I know this word but not all of its senses', 'I have heard of this word but no not know what it means', 'I have not heard of this word']
        for (const option of options) {
            let nobreak = document.createElement('nobr')
            let input = document.createElement("input");
            input.type = "radio"
            input.name = 'word_knowledge'
            input.id = `word_knowledge:${index}`
            input.onclick = function () {
                that.word_knowledge = option
                // word_knowledge_cell.style.color = 'green'
                console.log(`Selected word knowledge ${option}`)
            }
            let label = document.createElement("label");
            label.htmlFor = `word_knowledge:${index}`
            label.innerHTML += option
            nobreak.appendChild(input)
            nobreak.appendChild(label)
            word_knowledge_cell.appendChild(nobreak)
            nobreak.appendChild(document.createElement("br"))
            if (index === 0) {
                // Default to known
                that.word_knowledge = option
                input.checked = true
            }
            index++
        } */

        let footer_row = document.createElement("tr")
        footer_row.id = 'footer'
        footer_row.style.borderTop = '2px solid black'
        footer.appendChild(footer_row)
        table.appendChild(footer)

        let count_cell = document.createElement('td')
        count_cell.colSpan = '1'
        count_cell.style.paddingTop = `4px`
        count_cell.style.textAlign = 'left'
        count_cell.innerHTML = `<p style="color:grey">${this.manager.queue_index+1}/${this.manager.queue.length}</p>`
        footer_row.appendChild(count_cell)

        let submit_cell = document.createElement('td')
        submit_cell.colSpan = '5'
        submit_cell.style.paddingTop = `8px`
        submit_cell.style.textAlign = 'right'
        let submit = document.createElement("input");
        submit.type = "submit"

        let guidelines = document.createElement("button")
        guidelines.type = 'button'
        guidelines.onclick = function () {
            that.lemma.screen.logs.log('open_guidelines', '', '')
            that.open_guidelines()
        }
        guidelines.innerHTML = 'Open Guidelines'

        let new_sense = document.createElement("button")
        new_sense.type = 'button'
        new_sense.onclick = function () {
            that.lemma.screen.logs.log('new_ghost_sense', '', '')
            that.lemma.new_ghost_sense()
        }
        new_sense.innerHTML = 'New Virtual Sense'

        let open_wordnet = document.createElement("button")
        open_wordnet.type = 'button'
        open_wordnet.onclick = function () {
            that.lemma.screen.logs.log('open_in_wordnet', '', '')
            that.open_wordnet(that.lemma.word)
        }
        open_wordnet.innerHTML = 'Open in WordNet'

        let open_google = document.createElement("button")
        open_google.type = 'button'
        open_google.onclick = function () {
            that.lemma.screen.logs.log('open_in_google', '', '')
            that.open_google(that.lemma.word)
        }
        open_google.innerHTML = 'Open in Google'

        let open_ety = document.createElement("button")
        open_ety.type = 'button'
        open_ety.onclick = function () {
            that.lemma.screen.logs.log('open_etymology', '', '')
            that.open_etymology(that.lemma.word)
        }
        open_ety.innerHTML = 'Open in Etymonline'

        submit_cell.appendChild(new_sense)
        let span = document.createElement('span')
        span.innerHTML = '&ensp;'
        submit_cell.appendChild(span)
        submit_cell.appendChild(guidelines)
        span = document.createElement('span')
        span.innerHTML = '&ensp;'
        submit_cell.appendChild(span)
        submit_cell.appendChild(open_wordnet)
        span = document.createElement('span')
        span.innerHTML = '&ensp;'
        submit_cell.appendChild(span)
        submit_cell.appendChild(open_google)
        span = document.createElement('span')
        span.innerHTML = '&ensp;'
        submit_cell.appendChild(span)
        submit_cell.appendChild(open_ety)
        span = document.createElement('span')
        span.innerHTML = '&ensp;'
        submit_cell.appendChild(span)
        submit_cell.appendChild(submit)
        footer_row.appendChild(submit_cell)

        // Free form input

        let footer_row_comments = document.createElement("tr")
        let comments_cell = document.createElement('td')
        comments_cell.style.verticalAlign = 'top'
        let comment_prompt = document.createElement("span")
        comment_prompt.style.color = 'grey'
        comment_prompt.innerHTML = 'Optional comments:'
        comments_cell.appendChild(comment_prompt)
        comments_cell.appendChild(document.createElement('br'))
        comments_cell.colSpan = '6'
        footer_row_comments.appendChild(comments_cell)
        footer.appendChild(comments_cell)
        this.comments_input = document.createElement('textarea')
        comments_cell.appendChild(this.comments_input)


        // Warning cell
        let footer_row_2 = document.createElement("tr")
        this.warning_cell = document.createElement('td')
        this.warning_cell.colSpan = '6'
        this.warning_cell.style.paddingTop = `8px`
        this.warning_cell.style.color = 'red'

        footer_row_2.appendChild(this.warning_cell)
        footer.appendChild(footer_row_2)

        // Submit logic
        form.onsubmit = function() {
            that.lemma.screen.logs.log('submit', '', '')
            return that.submit_annotation()
        }

        // Add
        element.innerHTML = '' // Remove loading screen
        element.appendChild(form)

        console.log(`Adding senses`)
        this.lemma.refresh()
    }

    open_guidelines() {
        console.log('Opening guidelines')
        window.open('documentation/ChainNet_Annotation_Guidelines.pdf')
        return false
    }

    open_wordnet(word) {
        window.open(`http://wordnetweb.princeton.edu/perl/webwn?s=${word}`)
        return false
    }

    open_google(word) {
        window.open(`https://www.google.com/search?q=${word}+definition`)
        return false
    }

    open_etymology(word) {
        window.open(`https://www.etymonline.com/search?q=${word}&type=0`)
        return false
    }

    submit_annotation() {

        // Extract data
        let issues = this.lemma.issues()
        if (issues.is_failed()) {
            this.warning_cell.innerHTML = '<b>Cannot submit:</b>\n<ul>'
            for (const issue of issues.get_issues()) {
                this.warning_cell.innerHTML += `<li>${issue}</li>\n`
            }
            this.warning_cell.innerHTML+='</ul>'
            return false
        }

        const return_data = this.lemma.get_data()
        save_lemma(this.manager.user_id, this.manager.queue_name, this.lemma.lemma_name, return_data, this.known_box.checked, this.comments_input.value).then(() => {

            // Extract features
            let feature_frequencies = this.manager.datastore.feature_frequencies
            const lemma_features = this.lemma.get_feature_list()

            for (const feature of lemma_features) {
                if (feature in feature_frequencies) {
                    feature_frequencies[feature] += 1
                } else {
                    feature_frequencies[feature] = 1
                }
            }

            save_features(this.manager.user_id, feature_frequencies).then(() => {
                save_logs(this.manager.user_id, this.logs.get_data(), this.lemma.lemma_name, this.manager.queue_name).then(() => {
                    // Next word
                    this.manager.update_queue_and_render()
                })
            })
        })

        return false
    }
}