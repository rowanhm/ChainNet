import {is_valid_feature, make_empty_cell} from "../../utilities.js";
import {WordNetDefinition} from "../definition/wordnet_definition.js";
import {CustomDefinition} from "../definition/custom_definition.js";
import {autocomplete} from "../../autocompletion.js";

export class Sense {

    constructor(sense) {
        this.insane = true

        if (sense !== null) {
            this.lemma = sense.lemma
            this.known = sense.known
            this.new_sense_id = sense.new_sense_id
            this.name_cell = sense.name_cell
            this.label_selector_cell = sense.label_selector_cell
            this.relation_cell = sense.relation_cell
            this.tool_cell = sense.tool_cell
            this.row = sense.row
            this.definition = sense.definition
            this.backend_sense_id = sense.backend_sense_id
            this.feature_cell = sense.feature_cell
            this.definition.sense = this
            this.label_options = sense.label_options
            this.is_mixed = sense.is_mixed
            this.is_ghost = sense.is_ghost
            this.subcore = sense.subcore
            this.features_inputs = sense.features_inputs
            this.features_index = sense.features_index
        }

        this.label = null
        this.border_pattern = '1px solid black'
    }

    reset_local_features() {
        this.features_inputs = {}
        this.features_index = 0
        this.insane = true
    }

    get_backend_sense_id() {
        if (this.is_mixed) {
            if (this.get_label() !== 'Metaphorical') {
                return `A_${this.backend_sense_id}`
            } else {
                return `B_${this.backend_sense_id}`
            }
        }
        return this.backend_sense_id
    }

    is_subcore() {
        this.sanify()
        return this.subcore
    }

    set_subcore(value) {
        if (value !== this.is_subcore()) {
            this.subcore = value
            this.lemma.mark_all_insane()
            this.lemma.refresh()
        }
    }

    issues() {
        let issues = this.definition.issues()
        if (this.get_label() === null) {
            issues.add_issue(`${this.get_outward_facing_id()} is unlabelled.`)
        }
        for (const feature of this.get_feature_list()) {
            if (!(is_valid_feature(feature))) {
                issues.add_issue(`${this.get_outward_facing_id()} has an invalid feature (features must not be blank and must not contain '.', '#', '$', '/', '[', or ']').`)
            }
        }
        return issues
    }

    get_feature_list() {
        this.sanify()
        let features = []
        for (const [feature_id, feature_input] of Object.entries(this.features_inputs)) {
            features.push(feature_input.value)
        }
        return features
    }

    get_label() {
        return this.label
    }

    mark_insane() {
        this.insane = true
    }

    sanify() {
        if (this.insane) {
            this.insane = false
        }
    }

    add_feature() {
        let new_feature = document.createElement('input')
        new_feature.type = 'text'
        new_feature.size = "30"
        let that = this
        new_feature.oninput = function () {
            that.refresh_text()
        }
        this.features_inputs[`${this.new_sense_id}:${this.features_index}`] = new_feature
        this.features_index++
        this.insane = true
        this.lemma.refresh()
        // Add this line back for autocomplete:
        // autocomplete(new_feature, this.lemma.datastore.feature_list)
    }

    delete_feature(feature_id) {
        delete this.features_inputs[feature_id]
        this.insane = true
        for (const sense of this.lemma.metaphorical_senses()) {
            sense.insane = true
        }
        this.lemma.refresh()
    }

    get_features() {
        this.sanify()
        let features = {}
        for (const [feature_id, feature_input] of Object.entries(this.features_inputs)) {
            features[feature_id] = feature_input.value
        }
        return features
    }

    get_feature(feature_id) {
        //this.sanify()
        //return this.features_inputs[feature_id].value
        return this.get_features()[feature_id]
    }

    get_feature_inputs() {
        this.sanify()
        return this.features_inputs
    }

    build_cells(defn='') {
        this.row = document.createElement("tr");
        this.row.style.borderTop = this.border_pattern
        this.name_cell = make_empty_cell()
        this.name_cell.style.textAlign = 'center'
        this.tool_cell = make_empty_cell()
        this.tool_cell.style.backgroundColor='white'
        this.tool_cell.style.textAlign = 'center'
        this.label_selector_cell = make_empty_cell()
        this.relation_cell = make_empty_cell()
        this.feature_cell = make_empty_cell()
        this.feature_cell.style.verticalAlign = 'bottom'
        this.definition.make_definition_cell(defn)
        // this.definition.make_image_cell()
        this.make_row()
    }

    initialise_wordnet_sense(lemma, wordnet_sense_id, new_sense_id) {
        this.lemma = lemma
        this.backend_sense_id = `wordnet:${wordnet_sense_id}`
        this.new_sense_id = new_sense_id
        this.definition = new WordNetDefinition(lemma, wordnet_sense_id)
        this.is_mixed = false
        this.is_ghost = false
        this.known = true
        this.subcore = false
        this.reset_local_features()
        // Only literal half will be created this ways -- other initialised as met
        this.label_options = ['Literal', 'Related', 'Metaphorical']
        this.build_cells()
    }

    initialise_custom_sense(lemma, new_sense_id) {
        this.lemma = lemma
        this.backend_sense_id = `new:${this.lemma.get_next_new_sense_id()}`
        this.new_sense_id = new_sense_id
        this.definition = new CustomDefinition(this)
        this.label_options = ['Related']
        this.is_mixed = false
        this.is_ghost = true
        this.known = true
        this.subcore = false
        this.reset_local_features()
        this.build_cells()
    }

    get_row() {
        this.make_row()
        return this.row
    }

    get_outward_facing_id() {
        if (this.backend_sense_id.substring(0, 8) === 'wordnet:') {
            return `${this.lemma.datastore.senses_to_info[this.backend_sense_id.substring(8)]['word']}(${this.new_sense_id})`
        } else {
            return `${this.lemma.word}(${this.new_sense_id})`
        }
    }

    fill_name_cell() {
        this.name_cell.innerHTML = '<b>' + this.get_outward_facing_id() + '</b><br>'
        if (!this.issues().is_failed()) {
            this.name_cell.style.color = 'green'
        } else {
            this.name_cell.style.color = 'red'
        }

        let known = document.createElement('nobr')
        known.style.fontSize = '80%'
        known.innerHTML = 'known? '
        let checkbox = document.createElement('input')
        checkbox.type = 'checkbox'
        if (this.known) {
            checkbox.checked = true
        }
        known.appendChild(checkbox)
        known.style.color = 'grey'
        let that = this
        checkbox.onclick = function () {
            that.known = !that.known
            that.lemma.update_word_known()
        }
        this.name_cell.appendChild(known)
    }

    fill_tool_cell() {
        let that = this
        this.tool_cell.innerHTML = ''
        this.tool_cell.style.backgroundColor='white'
        this.tool_cell.style.textAlign = 'center'

        if (this.is_ghost) { // Delete button
            let delete_button = document.createElement("button")
            delete_button.type = 'button'
            delete_button.onclick = function () {
                that.lemma.screen.logs.log(`delete_virtual_sense`, that.get_backend_sense_id(), ``)
                that.lemma.delete_ghost_sense(that.new_sense_id)
            }
            delete_button.innerHTML = 'Delete'
            this.tool_cell.appendChild(delete_button)

        } else {

            if (!this.is_mixed) { // Split button
                let split_button = document.createElement("button")
                split_button.type = 'button'
                split_button.onclick = function () {
                    that.lemma.screen.logs.log(`split`, that.get_backend_sense_id(), ``)
                    that.lemma.split_mixed_sense(that.new_sense_id)
                }
                split_button.innerHTML = 'Split'
                this.tool_cell.appendChild(split_button)

            } else { // Merge button
                if (this.get_label() !== 'Metaphorical') {
                    this.tool_cell.rowSpan = "2"

                    let remerge_button = document.createElement("button")
                    remerge_button.type = 'button'
                    remerge_button.onclick = function () {
                        that.lemma.screen.logs.log(`remerge`, that.get_backend_sense_id(), ``)
                        that.lemma.merge_mixed_sense(that.new_sense_id)
                    }
                    remerge_button.innerHTML = '<nobr>Re-merge</nobr>'
                    this.tool_cell.appendChild(remerge_button)
                }
            }
        }
    }

    fill_label_cell() {
        this.label_selector_cell.innerHTML = ''

        if (this.label_options.length > 1) {
            let that = this
            const select_name = `${this.new_sense_id}:label_assign`
            for (const option of this.label_options) {
                let no_break = document.createElement('nobr')
                const name = `${this.new_sense_id}:label_assign:${option}`

                let input = document.createElement("input");
                input.type = "radio"
                input.name = select_name
                input.id = name
                no_break.appendChild(input)

                let label = document.createElement("label");
                label.htmlFor = name
                let option_text = ''
                if (option === 'Literal') {
                    label.style.color = '#772206'
                    option_text = 'Core'
                } else if (option === 'Related') {
                    label.style.color = '#D04C18'
                    option_text = 'Associated'
                } else if (option === 'Metaphorical') {
                    label.style.color = '#8F45A3'
                    option_text = 'Metaphorical'
                } else {
                    console.error('Invalid label')
                }
                label.innerHTML = option_text

                input.onclick = function () {
                    that.lemma.screen.logs.log(option_text.toLowerCase(), that.get_backend_sense_id(), '')
                    that.lemma.set_label(that.new_sense_id, option.toLowerCase())
                }

                if (option === this.get_label()) {
                    input.checked = true
                } else if (this.get_label() !== null) {
                    // Something is selected that isn't this
                    // label.innerHTML = '<s>' + label.innerHTML + '</s>'
                    label.style.opacity = '0.5'
                }


                no_break.appendChild(label)

                if ((option === this.get_label()) && (option === "Metaphorical" || option === "Related")) {

                    // Add secondary core option
                    let subcore_element = document.createElement('span')
                    let label = document.createElement("label");
                    let subname = `${this.new_sense_id}:subcore`
                    label.htmlFor = subname
                    label.innerHTML = '&nbsp;+ Conduit? '
                    subcore_element.appendChild(label)

                    let checkbox = document.createElement('input')
                    checkbox.type = 'checkbox'
                    checkbox.id = subname
                    if (this.is_subcore()) {
                        checkbox.checked = true
                    } else {
                        label.style.opacity = '0.5'
                    }
                    subcore_element.appendChild(checkbox)
                    // subcore_element.style.color = 'grey'
                    let that = this
                    subcore_element.onclick = function () {
                        let is_subcore = that.is_subcore()
                        if (!is_subcore) {
                            that.lemma.screen.logs.log(`promote_to_secondary_core`, that.get_backend_sense_id(), ``)
                        } else {
                            that.lemma.screen.logs.log(`demote_from_secondary_core`, that.get_backend_sense_id(), ``)
                        }
                        that.set_subcore(!is_subcore)
                    }
                    no_break.appendChild(subcore_element)
                }

                no_break.appendChild(document.createElement("br"))
                this.label_selector_cell.appendChild(no_break)

            }
        } else {


            let no_break = document.createElement("nobr")
            let option = this.label_options[0]
            let label = document.createElement("span")
            if (option === 'Literal') {
                label.style.color = '#772206'
                label.innerHTML = 'Core'
            } else if (option === 'Related') {
                label.style.color = '#D04C18'
                label.innerHTML = 'Associated'
            } else if (option === 'Metaphorical') {
                label.style.color = '#8F45A3'
                label.innerHTML = 'Metaphorical'
            } else {
                console.error('Invalid label')
            }

            no_break.appendChild(label)
            this.label_selector_cell.appendChild(no_break)

            // Add conduit
            if (this.label_options[0] === "Metaphorical" || this.label_options[0] === "Related") {

                // Add secondary core option
                let subcore_element = document.createElement('span')
                let label = document.createElement("label");
                let subname = `${this.new_sense_id}:subcore`
                label.htmlFor = subname
                label.innerHTML = '&nbsp;+ Conduit? '
                subcore_element.appendChild(label)

                let checkbox = document.createElement('input')
                checkbox.type = 'checkbox'
                checkbox.id = subname
                if (this.is_subcore()) {
                    checkbox.checked = true
                } else {
                    label.style.opacity = '0.5'
                }
                subcore_element.appendChild(checkbox)
                // subcore_element.style.color = 'grey'
                let that = this
                subcore_element.onclick = function () {
                    let is_subcore = that.is_subcore()
                    if (!is_subcore) {
                        that.lemma.screen.logs.log(`promote_to_secondary_core`, that.get_backend_sense_id(), ``)
                    } else {
                        that.lemma.screen.logs.log(`demote_from_secondary_core`, that.get_backend_sense_id(), ``)
                    }
                    that.set_subcore(!is_subcore)
                }
                no_break.appendChild(subcore_element)
            }
        }
    }

    fill_relation_cell() {
        this.relation_cell.innerHTML = ''
    }

    fill_features_cell() {
        this.feature_cell.innerHTML = ''

        let subtable = document.createElement('table')
        subtable.style.marginRight = '0'
        subtable.style.marginLeft = 'auto'
        subtable = this.fill_features_table(subtable)
        this.feature_cell.appendChild(subtable)
    }

    fill_features_table(subtable) {
        const features = this.get_feature_inputs()
        let that = this

        for (const [feature_id, feature_input] of Object.entries(features)) {
            let row = document.createElement('tr')

            let feature_cell = document.createElement('td')
            feature_cell.style.textAlign = 'left'
            feature_cell.colSpan = "2"

            row.appendChild(feature_cell)
            let no_break = document.createElement('nobr')
            no_break.innerHTML = 'This thing ' // This thing
            let new_feature_wrapper = document.createElement('div')
            new_feature_wrapper.className = 'autocomplete'
            new_feature_wrapper.appendChild(feature_input)
            no_break.appendChild(new_feature_wrapper)
            feature_cell.appendChild(no_break)

            // let delete_cell = document.createElement('td')
            //row.appendChild(delete_cell)
            let delete_button = document.createElement("button")
            delete_button.type = 'button'
            delete_button.onclick = function () {
                that.lemma.screen.logs.log('delete_feature', that.get_backend_sense_id(), `feature_${feature_id}`)
                that.delete_feature(feature_id)
            }
            delete_button.innerHTML = '&minus;'
            let space = document.createElement('span')
            space.innerHTML = ' '
            no_break.appendChild(space)
            no_break.appendChild(delete_button)
            // delete_cell.style.textAlign = 'right'

            subtable.appendChild(row)
        }

        // Check if it needs to add an "add" button
        let connected = false
        for (const sense of this.lemma.metaphorical_senses()) {
            if (sense.get_resembles() === this.new_sense_id) {
                connected = true
                break
            }
        }
        if (connected) {
            // Add 'add' button
            let add_row = document.createElement('tr')
            let add_cell = document.createElement('td')
            add_cell.colSpan = '2'
            add_cell.style.textAlign = 'right'
            let create_button = document.createElement("button")
            create_button.type = 'button'
            create_button.onclick = function () {
                that.lemma.screen.logs.log('new_feature', that.get_backend_sense_id(), '')
                that.add_feature()
            }
            create_button.innerHTML = '+'
            add_row.appendChild(add_cell)
            add_cell.appendChild(create_button)
            subtable.appendChild(add_cell)
        }

        // Add 'add' button
        return subtable
    }

    make_row() {
        // Fill all cells
        this.fill_name_cell()
        this.fill_label_cell()
        this.fill_relation_cell()
        this.fill_features_cell()
        this.fill_tool_cell()

        // Attach all cells
        this.fill_row()
        this.set_colour()

    }

    fill_row() {
        this.row.innerHTML = ''
        this.row.appendChild(this.name_cell)
        this.row.appendChild(this.definition.definition_cell)
        // this.row.appendChild(this.definition.image_cell)
        this.row.appendChild(this.label_selector_cell)
        this.row.appendChild(this.relation_cell)
        this.row.appendChild(this.feature_cell)
        if ((!this.is_mixed) || (this.is_mixed && (this.get_label() !== 'Metaphorical'))) {
            // Don't add the tool cell for mixed metaphorical senses
            this.row.appendChild(this.tool_cell)
        }
    }

    set_colour() {
        this.row.style.backgroundColor = '#FFFFFF'
    }

    get_data() {
        let sense_data = {}
        sense_data['outward_id'] = this.new_sense_id
        sense_data['is_known'] = this.known
        sense_data['is_mixed'] = this.is_mixed
        sense_data['is_virtual'] = this.is_ghost
        let label = this.get_label()
        if (label === 'Literal') {
            label = 'core'
        } else if (label === 'Related') {
            label = 'association'
        } else if (label === 'Metaphorical') {
            label = 'metaphor'
        }
        sense_data['label'] = label
        sense_data['definition'] = this.definition.get_definition()

        sense_data['features'] = this.get_features()
        sense_data['is_conduit'] = this.is_subcore()
        return sense_data
    }

    make_definition_cell(){
        this.definition_cell = this.definition.make_definition_cell()
    }

    make_image_cell(){
        this.image_cell = this.definition.make_image_cell()
    }

    refresh_text() {
        for (const metaphorical_sense of this.lemma.metaphorical_senses()) {
            if (metaphorical_sense.new_sense_id !== this.new_sense_id) {
                metaphorical_sense.fill_features_cell()
            }
            metaphorical_sense.fill_name_cell()
        }
        this.fill_name_cell()
    }
}