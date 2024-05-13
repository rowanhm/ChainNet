import {load_features, load_json, save_features} from "./io.js";

export class Datastore {

    constructor() {
    }

    async load() {
        this.concepts_to_definitions = await load_json("bin/concepts_to_definitions.json");
        this.lemmas_to_senses = await load_json("bin/lemmas_to_senses.json");
        this.senses_to_info = await load_json("bin/senses_to_info.json");
        this.lemma_queues = await load_json("data/collection/queues.json")
    }

    async refresh_feature_list(user_id) {
        await load_features(user_id).then(async (snapshot) => {
            if (snapshot.exists()) {
                // Load the features of a user
                this.feature_frequencies = snapshot.val()
            } else {
                // If there is none, create a new set with just the default
                this.feature_frequencies = await load_json("data/collection/default_features.json")
                save_features(user_id, this.feature_frequencies)
            }
        })

        // Sort them by frequency
        this.feature_list = Object.keys(Object.entries(this.feature_frequencies)
            .sort(([, a], [, b]) => b - a)
            .reduce((r, [k, v]) => ({...r, [k]: v}), {}))
    }
}