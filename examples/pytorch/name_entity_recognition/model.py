


class Word2tag(nn.Module):
    def __init__(self, vocab, device=None):
        super(Word2tag, self).__init__()
        self.vocab = vocab
        self.device =device
        
        embedding_style = {'single_token_item': True if args.graph_type != 'ie' else False,
                            'emb_strategy': 'w2v_bilstm',
                            'num_rnn_layers': 1,
                            'bert_model_name': 'bert-base-uncased',
                            'bert_lower_case': True
                           }
        use_edge_weight = False
        if args.graph_type=='line_graph':
          if args.gnn_type=='ggnn':  
              self.graph_topology = LineBasedGraphConstruction(embedding_style=embedding_style,
                                                               vocab=vocab.in_word_vocab,
                                                               hidden_size=int(args.init_hidden_size/2), 
                                                               rnn_dropout=None,
                                                               word_dropout=args.word_dropout,
                                                               device=self.device,
                                                               fix_word_emb=not args.no_fix_word_emb,
                                                               fix_bert_emb=not args.no_fix_bert_emb)
          else:
              self.graph_topology = LineBasedGraphConstruction(embedding_style=embedding_style,
                                                               vocab=vocab.in_word_vocab,
                                                               hidden_size=args.init_hidden_size, 
                                                               rnn_dropout=None,
                                                               word_dropout=args.word_dropout, 
                                                               device=self.device,
                                                               fix_word_emb=not args.no_fix_word_emb,
                                                               fix_bert_emb=not args.no_fix_bert_emb)              
        if args.graph_type=='dependency_graph':
          if args.gnn_type=='ggnn': 
              self.graph_topology = DependencyBasedGraphConstruction_without_tokenizer(embedding_style=embedding_style,
                                                               vocab=vocab.in_word_vocab,
                                                               hidden_size=int(args.init_hidden_size/2), 
                                                               rnn_dropout=None,
                                                               word_dropout=args.word_dropout, 
                                                               device=self.device,
                                                               fix_word_emb=not args.no_fix_word_emb,
                                                               fix_bert_emb=not args.no_fix_bert_emb)
          else:
              self.graph_topology = DependencyBasedGraphConstruction_without_tokenizer(embedding_style=embedding_style,
                                                   vocab=vocab.in_word_vocab,
                                                   hidden_size=args.init_hidden_size, 
                                                   rnn_dropout=None,
                                                   word_dropout=args.word_dropout, 
                                                   device=self.device,
                                                   fix_word_emb=not args.no_fix_word_emb,
                                                   fix_bert_emb=not args.no_fix_bert_emb) 
        if args.graph_type=='node_emb':
            self.graph_topology = NodeEmbeddingBasedGraphConstruction(
                                    vocab.in_word_vocab,
                                    embedding_style,
                                    sim_metric_type=args.gl_metric_type,
                                    num_heads=args.gl_num_heads,
                                    top_k_neigh=args.gl_top_k,
                                    epsilon_neigh=args.gl_epsilon,
                                    smoothness_ratio=args.gl_smoothness_ratio,
                                    connectivity_ratio=args.gl_connectivity_ratio,
                                    sparsity_ratio=args.gl_sparsity_ratio,
                                    input_size=args.init_hidden_size,
                                    hidden_size=args.init_hidden_size,
                                    fix_word_emb=not args.no_fix_word_emb,
                                    fix_bert_emb=not args.no_fix_bert_emb,
                                    word_dropout=args.word_dropout,
                                    rnn_dropout=None,
                                    device=self.device)
            use_edge_weight = True  
            
        if args.graph_type=='node_emb_refined':        
            self.graph_topology = NodeEmbeddingBasedRefinedGraphConstruction(
                                    vocab.in_word_vocab,
                                    embedding_style,
                                    args.init_adj_alpha,
                                    sim_metric_type=args.gl_metric_type,
                                    num_heads=args.gl_num_heads,
                                    top_k_neigh=args.gl_top_k,
                                    epsilon_neigh=args.gl_epsilon,
                                    smoothness_ratio=args.gl_smoothness_ratio,
                                    connectivity_ratio=args.gl_connectivity_ratio,
                                    sparsity_ratio=args.gl_sparsity_ratio,
                                    input_size=args.init_hidden_size,
                                    hidden_size=args.init_hidden_size,
                                    fix_word_emb=not args.no_fix_word_emb,
                                    word_dropout=args.word_dropout,
                                    rnn_dropout=None,
                                    device=self.device)
            use_edge_weight = True        
        
        if 'w2v' in self.graph_topology.embedding_layer.word_emb_layers:
            self.word_emb = self.graph_topology.embedding_layer.word_emb_layers['w2v'].word_emb_layer
        else:
            self.word_emb = WordEmbedding(
                            self.vocab.in_word_vocab.embeddings.shape[0],
                            self.vocab.in_word_vocab.embeddings.shape[1],
                            pretrained_word_emb=self.vocab.in_word_vocab.embeddings,
                            fix_emb=not args.no_fix_word_emb,
                            device=self.device).word_emb_layer      
            
        self.gnn_type=args.gnn_type
        self.use_gnn=args.use_gnn
        self.linear0=nn.Linear(int(args.init_hidden_size*1), args.hidden_size).to(self.device)
        self.linear0_=nn.Linear(int(args.init_hidden_size*1), args.init_hidden_size).to(self.device)        
        self.dropout_tag = nn.Dropout(args.tag_dropout)
        self.dropout_rnn_out = nn.Dropout(p=args.rnn_dropout)
        if self.use_gnn is False:
              self.bilstmcrf=SentenceBiLSTMCRF(device=self.device, use_rnn=False).to(self.device) 
        else:   
            if self.gnn_type=="graphsage":   
               if args.direction_option=='bi_sep':
                   self.gnn = GraphSAGE(args.gnn_num_layers, args.hidden_size, int(args.init_hidden_size/2), int(args.init_hidden_size/2), aggregator_type='mean',direction_option=args.direction_option, activation=F.elu).to(self.device)        
               else:                   
                   self.gnn = GraphSAGE(args.gnn_num_layers, args.hidden_size, args.init_hidden_size, args.init_hidden_size, aggregator_type='mean',direction_option=args.direction_option, activation=F.elu).to(self.device)        
               self.bilstmcrf=SentenceBiLSTMCRF(device=self.device, use_rnn=True).to(self.device)
            elif self.gnn_type=="ggnn":
               if args.direction_option=='bi_sep':
                  self.gnn = GGNN(args.gnn_num_layers, int(args.init_hidden_size/2), int(args.init_hidden_size/2),direction_option=args.direction_option,n_etypes=1).to(self.device)        
               else:    
                  self.gnn = GGNN(args.gnn_num_layers, args.init_hidden_size, args.init_hidden_size,direction_option=args.direction_option,n_etypes=1).to(self.device)        
               self.bilstmcrf=SentenceBiLSTMCRF(device=self.device,use_rnn=True).to(self.device)            
            elif self.gnn_type=="gat":
               heads = 2
               if args.direction_option=='bi_sep': 
                   self.gnn = GAT(args.gnn_num_layers,args.hidden_size,int(args.init_hidden_size/2),int(args.init_hidden_size/2), heads,direction_option=args.direction_option,feat_drop=0.6, attn_drop=0.6, negative_slope=0.2, activation=F.elu).to(self.device)                                    
               else:
                   self.gnn = GAT(args.gnn_num_layers,args.hidden_size,args.init_hidden_size,args.init_hidden_size, heads,direction_option=args.direction_option,feat_drop=0.6, attn_drop=0.6, negative_slope=0.2, activation=F.elu).to(self.device)        
               self.bilstmcrf=SentenceBiLSTMCRF(device=self.device, use_rnn=True).to(self.device)
            elif self.gnn_type=="gcn":   
               if args.direction_option=='bi_sep':
                   self.gnn = GCN(args.gnn_num_layers, args.hidden_size, int(args.init_hidden_size/2), int(args.init_hidden_size/2), direction_option=args.direction_option, activation=F.elu).to(self.device)        
               else:                   
                   self.gnn = GCN(args.gnn_num_layers, args.hidden_size, args.init_hidden_size, args.init_hidden_size,direction_option=args.direction_option, activation=F.elu).to(self.device)        
               self.bilstmcrf=SentenceBiLSTMCRF(device=self.device,use_rnn=True).to(self.device)
              
     

    def forward(self, graph, tgt=None, require_loss=True):
        batch_graph = self.graph_topology(graph)

        if self.use_gnn is False:
            batch_graph.node_features['node_emb']=batch_graph.node_features['node_feat']
            batch_graph.node_features['node_emb']=self.dropout_tag(F.elu(self.linear0_(self.dropout_rnn_out(batch_graph.node_features['node_emb']))))             
            
        else:
           # run GNN
           if self.gnn_type=="ggnn":
               batch_graph.node_features['node_feat']=batch_graph.node_features['node_feat']                                   
           else:    
               batch_graph.node_features['node_feat']=self.dropout_tag(F.elu(self.linear0(self.dropout_rnn_out(batch_graph.node_features['node_feat']))))                          
               
           batch_graph = self.gnn(batch_graph)
               
        
        # down-task
        loss,pred=self.bilstmcrf(batch_graph,tgt)
        self.loss=loss
        
        if require_loss==True:
           return pred, self.loss
        else:
            loss=None
            return pred, self.loss

    def save_checkpoint(self, save_path, checkpoint_name):
        """
            The API for saving the model.
        Parameters
        ----------
        save_path : str
            The root path.
        checkpoint_name : str
            The name of the checkpoint.
        Returns
        -------

        """
        checkpoint_path = os.path.join(save_path, checkpoint_name)
        os.makedirs(save_path, exist_ok=True)
        torch.save(self, checkpoint_path)


    @classmethod
    def load_checkpoint(cls, load_path, checkpoint_name):
        """
            The API to load the model.

        Parameters
        ----------
        load_path : str
            The root path to load the model.
        checkpoint_name : str
            The name of the model to be loaded.

        Returns
        -------
        Graph2XBase
        """
        checkpoint_path = os.path.join(load_path, checkpoint_name)
        model = torch.load(checkpoint_path)
        return model