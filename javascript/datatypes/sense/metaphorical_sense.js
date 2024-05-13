import {Sense} from "./sense.js";
import {LiteralSense} from "./literal_sense.js";
//import {autocomplete} from "../../autocompletion.js";
import {is_valid_feature} from "../../utilities.js";

export class MetaphoricalSense extends Sense {

    // Handles extra info of metaphors (derived from, grouping)

    constructor(sense) {
        super(sense);
        this.resembles = null
        this.label = 'Metaphorical'
        this.reset_features()
    }


    set_feature_label(feature_id, label) {
        this.feature_labels[feature_id] = label
        this.insane = true
        this.lemma.mark_all_insane()
        this.lemma.refresh()
    }

    get_feature_label(feature_id) {
        this.sanify()
        return this.feature_labels[feature_id]
    }

    get_feature_labels() {
        this.sanify()
        return this.feature_labels
    }

    get_transformation_input(feature_id) {
        this.sanify()
        return this.feature_transformation_inputs[feature_id]
    }

    get_transformations() {
        this.sanify()
        let output = {}
        for (const [feature_id, transformation_input] of Object.entries(this.feature_transformation_inputs)) {
            output[feature_id] = transformation_input.value
        }
        return output
    }

    get_resembles() {
        this.sanify()
        return this.resembles
    }

    set_resembles(sense_id) {
        if (this.resembles !== sense_id) {
            this.reset_features()
            this.resembles = sense_id
            this.insane = true
            this.lemma.refresh()
        }
    }

    reset_features() {
        this.feature_labels = {}
        this.feature_transformation_inputs = {}
        this.insane = true
    }

    sanify() {
        if (this.insane) {
            // Make sure the thing it resembles is a literal
            let resembles_sense = null
            if (this.is_mixed) {
                // Set resembles to other half
                this.resembles = this.new_sense_id.slice(0, -1) + 'A'
            } else {
                if (this.resembles !== null) {
                    resembles_sense = this.lemma.get_sense(this.resembles)

                    if (!this.lemma.new_id_order.includes(this.resembles)) {
                        this.resembles = null
                    } else if (!(this.is_valid_connection(resembles_sense))) {
                        this.resembles = null
                    }
                }
            }

            // Handle features
            if (this.resembles !== null) {

                resembles_sense = this.lemma.get_sense(this.resembles)

                let found_features = new Set()

                const features = resembles_sense.get_features()
                // Create feature_labels for missing features
                for (const [feature_id, feature_text] of Object.entries(features)) {
                    found_features.add(feature_id)
                    if (!(feature_id in this.feature_labels)) {
                        this.feature_labels[feature_id] = null
                    }
                }

                // Remove feature_labels for features not in literal parent
                // Remove feature_transformations for features not in literal parent
                let that = this
                for (const [feature_id, feature_label] of Object.entries(this.feature_labels)) {
                    if (!(found_features.has(feature_id))) {
                        delete this.feature_labels[feature_id]
                        if (feature_id in this.feature_transformation_inputs) {
                            delete this.feature_transformation_inputs[feature_id]
                        }
                    } else {
                        // Is contained
                        if (this.feature_labels[feature_id] !== 'modified') {
                            if (feature_id in this.feature_transformation_inputs) {
                                delete this.feature_transformation_inputs[feature_id]
                            }
                        } else {
                            if (!(feature_id in this.feature_transformation_inputs)) {
                                // Add the transformation
                                // If it is transformed, initialise the value with the same text
                                let feature_transformation_input = document.createElement('input')
                                feature_transformation_input.oninput = function() {
                                    that.fill_name_cell()
                                }
                                feature_transformation_input.type = 'text'
                                feature_transformation_input.size = "30"
                                feature_transformation_input.value = this.lemma.get_sense(this.resembles).get_feature(feature_id)
                                //autocomplete(feature_transformation_input, this.lemma.datastore.feature_list)
                                feature_transformation_input.oninput = function () {
                                    that.refresh_text()
                                }
                                this.feature_transformation_inputs[feature_id] = feature_transformation_input
                            }
                        }
                    }
                }

            } else {
                // Reset features
                this.reset_features()
            }
            this.insane = false
        }
    }

    set_colour() {
        this.row.style.backgroundColor = '#FBE8FF'
    }

    is_valid_connection(other_sense) {
        return ((other_sense instanceof LiteralSense)) ||
            ((other_sense instanceof MetaphoricalSense && other_sense.is_subcore() && other_sense.new_sense_id !== this.new_sense_id))
    }

    fill_relation_cell() {
        if (!this.is_mixed) {
            // Make dropdown selection
            this.relation_cell.innerHTML = ''

            let resemblance_cell = document.createElement('nobr')
            //resemblance_cell.innerHTML = 'Connects to '

            let select_resemblance = document.createElement("select");
            select_resemblance.id = `${this.new_sense_id}:resemblance_select`
            let that = this
            select_resemblance.onchange = function () {
                that.lemma.screen.logs.log('connect', that.get_backend_sense_id(), that.lemma.get_sense(document.getElementById(`${that.new_sense_id}:resemblance_select`).value).get_backend_sense_id())
                that.update_resembles()
            }

            let blank_option = document.createElement("option");
            blank_option.value = null
            blank_option.disabled = true
            blank_option.hidden = true
            blank_option.innerHTML = 'select';
            select_resemblance.appendChild(blank_option)

            // Add options
            let found_resembles = false
            if (this.get_resembles() === null) {
                blank_option.selected = true
                found_resembles = true
            }
            for (const other_sense of this.lemma.all_senses()) {
                const other_sense_id = other_sense.new_sense_id
                let option = document.createElement("option");
                option.value = other_sense_id;
                option.text = other_sense.get_outward_facing_id();
                if (this.is_valid_connection(other_sense)) {
                    if (other_sense_id === this.get_resembles()) {
                        // Select
                        option.selected = true
                        found_resembles = true
                    }
                } else {
                    // Hide
                    option.disabled = true
                }
                select_resemblance.appendChild(option);
            }
            if (!found_resembles) {
                console.error(`Failed to find resembled (${this.new_sense_id} resembles ${this.get_resembles()})`)
            }

            resemblance_cell.appendChild(select_resemblance)
            this.relation_cell.appendChild(resemblance_cell)
        } else {
            this.relation_cell.innerHTML = this.lemma.get_sense(this.get_resembles()).get_outward_facing_id();
        }
    }

    make_text_row(text) {
        let instruction_row = document.createElement('tr')
        let instruction_cell = document.createElement('td')
        instruction_cell.colSpan = "2"
        instruction_row.style.textAlign = 'left'
        let instruction_box = document.createElement('nobr')
        let instruction_text = document.createElement('i')
        instruction_text.innerHTML = text
        instruction_box.appendChild(instruction_text)
        instruction_cell.appendChild(instruction_box)
        instruction_row.appendChild(instruction_box)
        return instruction_row
    }

    fill_features_table(subtable) {
        const resembles_sense = this.lemma.get_sense(this.get_resembles())
        if (this.get_resembles() === null) {
            // No resembled sense selected
            subtable.appendChild(this.make_text_row('')) // 'Select which sense this connects to'
        } else {
            const features = resembles_sense.get_features()
            if (Object.keys(features).length === 0) {
                // No features
                subtable.appendChild(this.make_text_row(`Add features to ${resembles_sense.get_outward_facing_id()}`))
            } else {
                // Iterate through the shared features and the mapping
                for (const [feature_id, feature_text] of Object.entries(features)) {
                    let row = document.createElement('tr')
                    subtable.appendChild(row)

                    const feature_label = this.get_feature_label(feature_id)

                    // Add text
                    let text_cell = document.createElement('td')
                    text_cell.style.textAlign = 'left'
                    let no_break = document.createElement('nobr')
                    no_break.innerHTML = `This thing ${feature_text}`

                    //no_break.innerHTML = `This ${feature_text}`
                    if (feature_label === 'kept') {
                        no_break.style.color = 'green'
                    } else if (feature_label === 'lost') {
                        no_break.innerHTML = `<s>This thing ${feature_text}</s>`
                        no_break.style.color = 'red'
                    } else if (feature_label === 'modified') {
                        no_break.style.color = '#F17400'
                    }

                    text_cell.appendChild(no_break)
                    row.appendChild(text_cell)

                    // Add options
                    let radio_cell = document.createElement('td')
                    radio_cell.style.textAlign = 'right'
                    let option_list = document.createElement('nobr')
                    row.appendChild(radio_cell)
                    radio_cell.appendChild(option_list)

                    const radio_name = `${this.new_sense_id}:feature_select_${feature_id}`
                    let that = this
                    for (const option of ['Kept', 'Lost', 'Modified']) {
                        const name = `${radio_name}:${option.toLowerCase()}`

                        let input = document.createElement("input");
                        input.type = "radio"
                        input.name = radio_name
                        input.id = name
                        input.onclick = function () {
                            that.lemma.screen.logs.log(`label_feature_${option.toLowerCase()}`, that.get_backend_sense_id(), `feature_${feature_id}`)
                            that.set_feature_label(feature_id, option.toLowerCase())
                        }
                        option_list.appendChild(input)

                        let label = document.createElement("label");
                        label.htmlFor = name
                        label.innerHTML += option

                        if (option.toLowerCase() === feature_label){
                            input.checked = true
                        } else if (feature_label === 'kept' || feature_label === 'lost' || feature_label === 'modified') {
                            label.style.opacity = '0.5'
                        }

                        option_list.appendChild(label)

                    }

                    // Add transformation row
                    if (feature_label === 'modified') {
                        let modification_row = document.createElement('tr')
                        let modification_cell = document.createElement('td')
                        modification_cell.style.textAlign = 'left'

                        let no_break = document.createElement('nobr')

                        subtable.appendChild(modification_row)
                        modification_row.appendChild(modification_cell)
                        modification_cell.colSpan = '2'

                        modification_cell.appendChild(no_break)
                        no_break.innerHTML = '&nbsp;&#8627; This thing '//'=> This thing '

                        // let feature_transformation_wrapper = document.createElement('div')
                        //feature_transformation_wrapper.className = 'autocomplete'
                        // feature_transformation_wrapper.appendChild(this.get_transformation_input(feature_id))

                        no_break.appendChild(this.get_transformation_input(feature_id))
                    }
                }
            }
        }
        return super.fill_features_table(subtable)
    }

    update_resembles() {
        const dropdown = document.getElementById(`${this.new_sense_id}:resemblance_select`)
        this.set_resembles(dropdown.value)
        console.log(`${this.new_sense_id} resembles ${this.resembles}`)
        this.lemma.refresh()
    }

    get_data() {
        let sense_data = super.get_data()
        sense_data['connected_to'] = this.lemma.get_sense(this.get_resembles()).get_backend_sense_id()
        sense_data['feature_map'] = this.get_feature_labels()
        sense_data['feature_modifications'] = this.get_transformations()
        return sense_data
    }

    issues() {
        let issues = super.issues()
        if (this.get_resembles() === null) {
            issues.add_issue(`${this.get_outward_facing_id()} is not connected to another sense.`)
        }
        let found_neg_feature = false
        let found_pos_feature = false
        let found_modified_feature = false
        for (const [feature_id, feature_label] of Object.entries(this.get_feature_labels())) {
            if (feature_label === 'kept') {
                found_pos_feature = true
            } else if (feature_label === 'lost') {
                found_neg_feature = true
            } else if (feature_label === 'modified') {
                if (!(is_valid_feature(this.get_transformation_input(feature_id).value))) {
                    issues.add_issue(`${this.get_outward_facing_id()} has an invalid feature modification (features must not be blank and must not contain '.', '#', '$', '/', '[', or ']').`)
                }
                if (this.get_transformation_input(feature_id).value === this.lemma.get_sense(this.get_resembles()).get_feature(feature_id)) {
                    issues.add_issue(`${this.get_outward_facing_id()} has an invalid feature modification (modified features must be different).`)
                }
                found_modified_feature = true
            } else {
                console.log('Metaphorical sense missing feature label')
                // feature is null
                issues.add_issue(`${this.get_outward_facing_id()} has features which are unlabelled (kept/lost/modified).`)
            }
        }
        if (!((found_neg_feature && found_pos_feature) || found_modified_feature)) {
            issues.add_issue(`${this.get_outward_facing_id()} does not have a sufficient feature transformation (it must have either a modified feature, or a kept feature and a lost feature).`)
        }
        return issues
    }

    get_features() {
        this.sanify()
        let features = {}
        // First add in features which are accepted of modified
        if (this.get_resembles() !== null) {
            for (const [feature_id, feature_text] of Object.entries(this.lemma.get_sense(this.get_resembles()).get_features())) {
                let label = this.get_feature_label(feature_id)
                if (label === 'kept') {
                    features[feature_id] = feature_text
                } else if (label === 'modified') {
                    features[`${feature_id}(M)`] = this.get_transformation_input(feature_id).value
                }
            }
        }
        // Now add in its new features
        for (const [feature_id, feature_input] of Object.entries(this.features_inputs)) {
            features[feature_id] = feature_input.value
        }
        return features
    }

    // This is for lemma aggregation
    get_feature_list() {
        this.sanify()
        let features = []
        for (const [feature_id, feature_input] of Object.entries(this.feature_transformation_inputs)) {
            features.push(feature_input.value)
        }
        return features
    }
}