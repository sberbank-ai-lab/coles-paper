import torch
import torch.nn as nn
import torch.nn.functional as F
from numpy.testing import assert_almost_equal

from .metric import outer_cosine_similarity


class ContrastiveLoss(nn.Module):
    """
    Contrastive loss
    
    "Signature verification using a siamese time delay neural network", NIPS 1993
    https://papers.nips.cc/paper/769-signature-verification-using-a-siamese-time-delay-neural-network.pdf
    """

    def __init__(self, margin, pair_selector):
        super(ContrastiveLoss, self).__init__()
        self.margin = margin
        self.pair_selector = pair_selector

    def forward(self, embeddings, target):
        
        positive_pairs, negative_pairs = self.pair_selector.get_pairs(embeddings, target)
        positive_loss = F.pairwise_distance(embeddings[positive_pairs[:, 0]], embeddings[positive_pairs[:, 1]]).pow(2)
        
        negative_loss = F.relu(
            self.margin - F.pairwise_distance(embeddings[negative_pairs[:, 0]], embeddings[negative_pairs[:, 1]])
        ).pow(2)
        loss = torch.cat([positive_loss, negative_loss], dim=0)
        
        return loss.sum(), len(positive_pairs) + len(negative_pairs)


class BinomialDevianceLoss(nn.Module):
    """
    Binomial Deviance loss

    "Deep Metric Learning for Person Re-Identification", ICPR2014
    https://arxiv.org/abs/1407.4979
    """

    def __init__(self, pair_selector, alpha = 1, beta = 1, C = 1):
        super(BinomialDevianceLoss, self).__init__()
        self.alpha = alpha
        self.beta = beta
        self.C = C
        self.pair_selector = pair_selector

    def forward(self, embeddings, target):
        
        positive_pairs, negative_pairs = self.pair_selector.get_pairs(embeddings, target)
        
        pos_pair_similarity = F.cosine_similarity(embeddings[positive_pairs[:, 0]], embeddings[positive_pairs[:, 1]], dim=1)
        neg_pair_similarity = F.cosine_similarity(embeddings[negative_pairs[:, 0]], embeddings[negative_pairs[:, 1]], dim=1)

        pos_loss = torch.mean(torch.log(1 + torch.exp(-self.alpha*(pos_pair_similarity - self.beta))))
        neg_loss = torch.mean(torch.log(1 + torch.exp(self.alpha*self.C*(neg_pair_similarity - self.beta))))

        res_loss = (pos_loss + neg_loss) * (len(target))
        
        return res_loss, len(positive_pairs) + len(negative_pairs)


class TripletLoss(nn.Module):
    """
    Triplets loss

    "Deep metric learning using triplet network", SIMBAD 2015
    https://arxiv.org/abs/1412.6622
    """

    def __init__(self, margin, triplet_selector):
        super(TripletLoss, self).__init__()
        self.margin = margin
        self.triplet_selector = triplet_selector

    def forward(self, embeddings, target):

        triplets = self.triplet_selector.get_triplets(embeddings, target)

        if embeddings.is_cuda:
            triplets = triplets.cuda()

        ap_distances = F.pairwise_distance(embeddings[triplets[:, 0]], embeddings[triplets[:, 1]]) # .pow(.5)
        an_distances = F.pairwise_distance(embeddings[triplets[:, 0]], embeddings[triplets[:, 2]])  # .pow(.5)
        losses = F.relu(ap_distances - an_distances + self.margin)

        return losses.sum(), len(triplets)


class HistogramLoss(torch.nn.Module):
    """
    HistogramLoss
    
    "Learning deep embeddings with histogram loss", NIPS 2016
    https://arxiv.org/abs/1611.00822
    code based on https://github.com/valerystrizh/pytorch-histogram-loss
    """
    
    def __init__(self, num_steps = 100, cuda=True):
        super(HistogramLoss, self).__init__()
        self.step = 2 / (num_steps - 1)
        self.eps = 1 / num_steps
        self.cuda = cuda
        self.t = torch.arange(-1, 1+self.step, self.step).view(-1, 1)
        self.tsize = self.t.size()[0]
        if self.cuda:
            self.t = self.t.cuda()
        
    def forward(self, embeddings, classes):
        def histogram(inds, size):
            
            s_repeat_ = s_repeat.clone()
            indsa = (s_repeat_floor - (self.t - self.step) > -self.eps) & (s_repeat_floor - (self.t - self.step) < self.eps) & inds

            assert indsa.nonzero().size()[0] == size, 'Another number of bins should be used'
            zeros = torch.zeros((1, indsa.size()[1])).byte()
            if self.cuda:
                zeros = zeros.cuda()
            indsb = torch.cat((indsa, zeros))[1:, :]
            s_repeat_[~(indsb|indsa)] = 0
            # indsa corresponds to the first condition of the second equation of the paper
            s_repeat_[indsa] = (s_repeat_ - self.t + self.step)[indsa] / self.step
            # indsb corresponds to the second condition of the second equation of the paper
            s_repeat_[indsb] =  (-s_repeat_ + self.t + self.step)[indsb] / self.step

            return s_repeat_.sum(1) / size
        
        # L2 normalization
        classes_size = classes.size()[0]
        classes_eq = (classes.repeat(classes_size, 1)  == classes.view(-1, 1).repeat(1, classes_size)).data
        dists = outer_cosine_similarity(embeddings)
        
        assert ((dists > 1 + self.eps).sum().item() + (dists < -1 - self.eps).sum().item()) == 0, 'L2 normalization should be used'
        s_inds = torch.triu(torch.ones(classes_eq.size()), 1).byte()
        if self.cuda:
            s_inds= s_inds.cuda()
        pos_inds = classes_eq[s_inds].repeat(self.tsize, 1)
        neg_inds = ~classes_eq[s_inds].repeat(self.tsize, 1)
        pos_size = classes_eq[s_inds].sum().item()
        neg_size = (~classes_eq[s_inds]).sum().item()
        s = dists[s_inds].view(1, -1)
        s_repeat = s.repeat(self.tsize, 1)
        s_repeat_floor = (torch.floor((s_repeat.data - 1e-6) / self.step) * self.step).float()
        
        histogram_pos = histogram(pos_inds, pos_size)
        assert_almost_equal(histogram_pos.sum().item(), 1, decimal=1, 
                            err_msg='Not good positive histogram', verbose=True)
        histogram_neg = histogram(neg_inds, neg_size)
        assert_almost_equal(histogram_neg.sum().item(), 1, decimal=1, 
                            err_msg='Not good negative histogram', verbose=True)
        histogram_pos_repeat = histogram_pos.view(-1, 1).repeat(1, histogram_pos.size()[0])
        histogram_pos_inds = torch.tril(torch.ones(histogram_pos_repeat.size()), -1).byte()
        if self.cuda:
            histogram_pos_inds = histogram_pos_inds.cuda()
        histogram_pos_repeat[histogram_pos_inds] = 0
        histogram_pos_cdf = histogram_pos_repeat.sum(0)
        loss = torch.sum(histogram_neg * histogram_pos_cdf)
        
        return loss, pos_size + neg_size


class MarginLoss(torch.nn.Module):
    
    """
    Margin loss
    
    "Sampling Matters in Deep Embedding Learning", ICCV 2017
    https://arxiv.org/abs/1706.07567

    """

    def __init__(self, pair_selector, margin=1, beta = 1.2):
        super(MarginLoss, self).__init__()
        self.margin = margin
        self.beta = beta
        self.pair_selector = pair_selector
        
    def forward(self, embeddings, target):

        positive_pairs, negative_pairs = self.pair_selector.get_pairs(embeddings, target)
        
        d_ap = F.pairwise_distance(embeddings[positive_pairs[:, 0]], embeddings[positive_pairs[:, 1]])
        d_an = F.pairwise_distance(embeddings[negative_pairs[:, 0]], embeddings[negative_pairs[:, 1]])

        pos_loss = torch.clamp(d_ap - self.beta + self.margin, min=0.0)
        neg_loss = torch.clamp(self.beta - d_an + self.margin, min=0.0)

        loss = torch.cat([pos_loss, neg_loss], dim=0)
        
        return loss.sum(), len(positive_pairs) + len(negative_pairs)

def get_loss(params, sampling_strategy):
    
    if params['train.loss'] == 'ContrastiveLoss':
        kwargs = {
            'margin' : params.get('train.margin', None),
            'pair_selector' : sampling_strategy
        }
        kwargs = {k:v for k,v in kwargs.items() if v is not None}
        loss_fn = ContrastiveLoss(**kwargs)
            
    elif params['train.loss'] == 'BinomialDevianceLoss':
        kwargs = {
            'C' : params.get('train.C', None),
            'alpha' : params.get('train.alpha', None),
            'beta' : params.get('train.beta', None),
            'pair_selector' : sampling_strategy
        }
        kwargs = {k:v for k,v in kwargs.items() if v is not None}
        loss_fn = BinomialDevianceLoss(**kwargs)       
            
    elif params['train.loss'] == 'TripletLoss':
        kwargs = {
            'margin' : params.get('train.margin', None),
            'triplet_selector' : sampling_strategy
        }
        kwargs = {k:v for k,v in kwargs.items() if v is not None}
        loss_fn = TripletLoss(**kwargs)
    
    elif params['train.loss'] == 'HistogramLoss':
        kwargs = {
            'num_steps' : params.get('train.num_steps', None),
        }
        kwargs = {k:v for k,v in kwargs.items() if v is not None}
        loss_fn = HistogramLoss(**kwargs)
        
    elif params['train.loss'] == 'MarginLoss':
        kwargs = {
            'margin' : params.get('train.margin', None),
            'beta' : params.get('train.beta', None),
            'pair_selector' : sampling_strategy
        }
        kwargs = {k:v for k,v in kwargs.items() if v is not None}
        loss_fn = MarginLoss(**kwargs)
    
    else:
         raise AttributeError(f'wrong loss "{params["train.loss"]}"')    

    def loss(*args, **kwargs):
        return loss_fn(*args, **kwargs)[0]
            
    return loss