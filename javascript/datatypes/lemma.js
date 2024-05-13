import {Sense} from "./sense/sense.js";
import {MetaphoricalSense} from "./sense/metaphorical_sense.js";
import {LiteralSense} from "./sense/literal_sense.js";
import {RelatedSense} from "./sense/related_sense.js";
import {Issues} from "./issues.js";
import {CustomDefinition} from "./definition/custom_definition.js";

export class Lemma {

    constructor(lemma_name, datastore, screen) {
        this.lemma_name = lemma_name
        this.datastore = datastore

        this.word = this.lemma_name.split(":")[0]
        this.pos = this.lemma_name.split(":")[1]

        // Make this a map of new_ids -> sense objects
        this.new_id_to_sense = new Map()
        this.new_id_order = []
        let i = 1
        for (const old_id of this.datastore.lemmas_to_senses[this.lemma_name]) {
            const new_id = i.toString()
            let sense = new Sense(null)
            sense.initialise_wordnet_sense(this, old_id, new_id)
            this.new_id_to_sense.set(new_id, sense)
            this.new_id_order.push(new_id)

            i++
        }
        this.next_available_index = i

        this.new_sense_id = 0

        this.screen = screen
        this.screen.logs.log('lemma_initialised', '', '')
    }

    update_word_known() {
        let sense_known = false
        for (const sense of this.all_senses()){
            if (sense.known) {
                sense_known = true
                break
            }
        }
        if (sense_known) {
            // Set the word to known
            if (this.screen.known_box.checked === false) {
                this.screen.known_box.checked = true
            }
        }
    }

    make_all_senses_unknown() {
        for (const sense of this.all_senses()){
            sense.known = false
        }
        this.refresh()
    }

    issues() {
        let issues = new Issues()
        for (const sense of this.all_senses()) {
            let sense_issues = sense.issues()
            issues.merge_issues(sense_issues)
        }
        return issues
    }

    get_next_new_sense_id() {
        this.new_sense_id += 1
        return this.new_sense_id
    }

    all_senses() {
        let output = []
        for (const new_id of this.new_id_order) {
            output.push(this.new_id_to_sense.get(new_id))
        }
        return output
    }

    metaphorical_senses() {
        let output = []
        for (const sense of this.all_senses()) {
            if (sense instanceof MetaphoricalSense) {
                output.push(sense)
            }
        }
        return output
    }

    literal_senses() {
        let output = []
        for (const sense of this.all_senses()) {
            if (sense instanceof LiteralSense) {
                output.push(sense)
            }
        }
        return output
    }

    get_sense(sense_id) {
        return this.new_id_to_sense.get(sense_id)
    }

    refresh() {
        this.mark_all_insane()
        let body = document.getElementById('table_body')
        body.innerHTML = ''
        for (const new_id of this.new_id_order) {
            const sense = this.new_id_to_sense.get(new_id)
            body.appendChild(sense.get_row())
        }
    }

    mark_all_insane() {
        for (const sense of this.all_senses()) {
            sense.mark_insane()
        }
    }

    new_ghost_sense() {
        const new_id = this.next_available_index.toString()
        this.next_available_index++
        let new_sense = new Sense(null)
        new_sense.initialise_custom_sense(this, new_id)
        new_sense = new RelatedSense(new_sense)

        this.new_id_to_sense.set(new_id, new_sense)
        this.new_id_order.splice(this.next_available_index, 0, new_id)

        this.refresh()
        //        this.set_label(new_sense, 'Related')
    }

    delete_ghost_sense(new_sense_id) {
        // Remove it
        const position = this.new_id_order.indexOf(new_sense_id)
        this.new_id_to_sense.delete(new_sense_id)
        this.new_id_order.splice(position, 1)

        this.refresh()
    }

    split_mixed_sense(new_sense_id) {
        let sense = this.new_id_to_sense.get(new_sense_id)
        const defn = sense.definition.create_definition_simple()
        let lit_half = new Sense(sense)
        lit_half.new_sense_id = new_sense_id+'A'
        lit_half.is_mixed = true
        lit_half.definition = new CustomDefinition(lit_half)
        lit_half.label_options = ['Literal', 'Related']
        lit_half.reset_local_features()
        lit_half.build_cells(defn)
        this.new_id_to_sense.set(lit_half.new_sense_id, lit_half)

        let met_half = new MetaphoricalSense(lit_half)
        met_half.new_sense_id = new_sense_id+'B'
        met_half.is_mixed = true
        met_half.definition = new CustomDefinition(met_half)
        met_half.label_options = ['Metaphorical']
        met_half.border_pattern = '1px dotted black'
        met_half.reset_local_features()
        met_half.build_cells(defn)
        this.new_id_to_sense.set(met_half.new_sense_id, met_half)

        // Replace
        const position = this.new_id_order.indexOf(new_sense_id)
        this.new_id_order.splice(position, 1, lit_half.new_sense_id, met_half.new_sense_id)

        this.refresh()
    }

    merge_mixed_sense(new_sense_id) {
        const base_sense_id = new_sense_id.slice(0, -1)

        this.new_id_to_sense.delete(base_sense_id + 'A')
        this.new_id_to_sense.delete(base_sense_id + 'B')

        const position = this.new_id_order.indexOf(base_sense_id + 'A')
        this.new_id_order.splice(position, 2, base_sense_id)

        // Reset it to unlabelled
        this.new_id_to_sense.set(base_sense_id,
            new Sense(this.new_id_to_sense.get(base_sense_id)))

        this.refresh()
    }

    set_label(new_sense_id, option) {
        let sense = this.new_id_to_sense.get(new_sense_id)
        let new_sense = null
        if (option === 'metaphorical') {
            new_sense = new MetaphoricalSense(sense)
        } else if (option === 'literal') {
            sense.set_subcore(false)
            new_sense = new LiteralSense(sense)
        } else if (option === 'related') {
            new_sense = new RelatedSense(sense)
        } else {
            console.error(`Invalid option for label change: ${option}`)
        }

        // Swap the senses:
        /* const position = this.new_id_order.indexOf(sense.new_sense_id)
        this.new_id_to_sense.delete(sense.new_sense_id)
        this.new_id_order.splice(position, 1)
        if (position === -1) {
            console.error('Inserting a sense to invalid position')
        } */
        this.new_id_to_sense.set(sense.new_sense_id, new_sense)
        // this.new_id_order.splice(position, 0, new_sense.new_sense_id)

        this.refresh()
    }

    get_data() {
        let return_data = {};

        let position = 0
        for (const sense of this.all_senses()) {
            const sense_id = sense.get_backend_sense_id()
            let data = sense.get_data()
            data['position'] = position  // Add the position in the lemma list
            position++
            return_data[sense_id] = data
        }
        return return_data
    }

    get_feature_list() {
        let features = []
        for (const sense of this.all_senses()) {
            features = features.concat(sense.get_feature_list())
        }
        return features
    }
}